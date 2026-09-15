"""Plugin QGIS: Roteirizador de Matrículas.

Sequencia visitas/vistorias entre matrículas georreferenciadas, por
distância em linha reta ou pela malha viária, e gera camadas de saída
com a ordem de visita e a rota resultante.
"""

import os

from qgis.core import (
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .core.csv_loader import CsvLoadError, load_points_from_csv
from .core.output_layers import build_output_layers
from .core.routing_service import DISTANCE_NETWORK, RoutingError, compute_route
from .roteirizador_dialog import RoteirizadorDialog

PLUGIN_MENU = "&Roteirizador de Matrículas"


class RoteirizadorMatriculasPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    # --------------------------------------------------------------- QGIS
    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon.svg")
        self.action = QAction(QIcon(icon_path), "Roteirizador de Matrículas", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(PLUGIN_MENU, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu(PLUGIN_MENU, self.action)
        self.iface.removeToolBarIcon(self.action)

    # ------------------------------------------------------------------ run
    def run(self):
        if self.dialog is None:
            self.dialog = RoteirizadorDialog(self.iface.mainWindow())

        if not self.dialog.exec_():
            return

        try:
            params = self.dialog.get_parameters()
        except ValueError as exc:
            QMessageBox.warning(self.iface.mainWindow(), "Roteirizador de Matrículas", str(exc))
            return

        try:
            self._execute(params)
        except (RoutingError, CsvLoadError) as exc:
            QMessageBox.critical(self.iface.mainWindow(), "Roteirizador de Matrículas", str(exc))

    # -------------------------------------------------------------- lógica
    def _execute(self, params):
        project = QgsProject.instance()

        if params["source_mode"] == "layer":
            source_layer = params["layer"]
        else:
            source_layer = load_points_from_csv(
                params["csv_path"], params["csv_x_field"], params["csv_y_field"], params["csv_crs"]
            )

        source_crs = source_layer.crs()
        points, fields, attributes, fids = self._extract_points(source_layer)

        if len(points) < 2:
            raise RoutingError(
                "A camada/arquivo de entrada precisa ter ao menos 2 matrículas com geometria de ponto válida."
            )

        distance_method = params["distance_method"]
        network_layer = params["network_layer"]
        working_crs = network_layer.crs() if distance_method == DISTANCE_NETWORK else source_crs

        if working_crs != source_crs:
            transform = QgsCoordinateTransform(source_crs, working_crs, project)
            points = [transform.transform(p) for p in points]

        start_mode = params["start_mode"]
        if start_mode == "selected_feature":
            selected_ids = source_layer.selectedFeatureIds()
            if len(selected_ids) != 1:
                raise RoutingError(
                    "Selecione exatamente 1 feição na camada de entrada para usar como ponto de partida."
                )
            try:
                start_index = fids.index(selected_ids[0])
            except ValueError as exc:
                raise RoutingError(
                    "A feição selecionada não possui geometria de ponto válida."
                ) from exc
        elif start_mode == "manual":
            manual_point = QgsPointXY(params["manual_x"], params["manual_y"])
            manual_crs = params["manual_crs"]
            if manual_crs != working_crs:
                transform = QgsCoordinateTransform(manual_crs, working_crs, project)
                manual_point = transform.transform(manual_point)
            points = [manual_point] + points
            attributes = [[]] + attributes
            start_index = 0
        else:  # centroid
            centroid = QgsGeometry.fromMultiPointXY(points).centroid().asPoint()
            points = [centroid] + points
            attributes = [[]] + attributes
            start_index = 0

        result = compute_route(
            points=points,
            crs=working_crs,
            start_index=start_index,
            method=distance_method,
            network_layer=network_layer,
        )

        points_layer, route_layer = build_output_layers(
            points=points,
            order=result["order"],
            matrix=result["matrix"],
            segments=result["segments"],
            source_fields=fields,
            source_attributes=attributes,
            crs=working_crs,
        )

        project.addMapLayer(points_layer)
        project.addMapLayer(route_layer)

        total_km = result["total_distance"] / 1000.0
        QMessageBox.information(
            self.iface.mainWindow(),
            "Roteirizador de Matrículas",
            f"Rota calculada com sucesso: {len(result['order'])} paradas, "
            f"distância total aproximada de {total_km:.2f} km.\n\n"
            f"Camadas adicionadas: \"{points_layer.name()}\" e \"{route_layer.name()}\".",
        )

    @staticmethod
    def _extract_points(layer):
        """Extrai pontos, campos, atributos e fids de uma camada vetorial.

        Feições sem geometria válida de ponto são ignoradas.
        """
        points = []
        attributes = []
        fids = []
        fields = layer.fields()
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom is None or geom.isEmpty():
                continue
            if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.PointGeometry:
                continue
            try:
                point = geom.asPoint()
            except Exception:
                continue
            points.append(QgsPointXY(point))
            attributes.append(feature.attributes())
            fids.append(feature.id())
        return points, fields, attributes, fids
