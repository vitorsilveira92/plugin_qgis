"""Diálogo do plugin Roteirizador de Matrículas.

Construído inteiramente em código (sem arquivo .ui) para evitar a
necessidade de compilar recursos com pyuic. Expõe ao usuário, de forma
explícita, a escolha entre calcular a rota por distância em linha reta
ou pela malha viária.
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayerProxyModel
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox, QgsProjectionSelectionWidget
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)

from .core.csv_loader import read_csv_header
from .core.routing_service import DISTANCE_NETWORK, DISTANCE_STRAIGHT


class RoteirizadorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Roteirizador de Matrículas")
        self.setMinimumWidth(460)
        self._build_ui()
        self._connect_signals()
        self._update_enabled_states()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(self._build_input_group())
        layout.addWidget(self._build_start_group())
        layout.addWidget(self._build_distance_group())

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _build_input_group(self):
        group = QGroupBox("Matrículas de entrada")
        v = QVBoxLayout(group)

        self.rb_input_layer = QRadioButton("Usar camada existente")
        self.rb_input_csv = QRadioButton("Importar de arquivo CSV")
        self.rb_input_layer.setChecked(True)
        v.addWidget(self.rb_input_layer)
        v.addWidget(self.rb_input_csv)

        self.cbo_input_layer = QgsMapLayerComboBox()
        self.cbo_input_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        v.addWidget(self.cbo_input_layer)

        csv_form = QFormLayout()
        self.file_csv = QgsFileWidget()
        self.file_csv.setFilter("Arquivos CSV (*.csv)")
        csv_form.addRow("Arquivo CSV:", self.file_csv)

        self.cbo_csv_x = QComboBox()
        self.cbo_csv_y = QComboBox()
        csv_form.addRow("Coluna X / Longitude:", self.cbo_csv_x)
        csv_form.addRow("Coluna Y / Latitude:", self.cbo_csv_y)

        self.crs_csv = QgsProjectionSelectionWidget()
        self.crs_csv.setCrs(QgsCoordinateReferenceSystem("EPSG:4674"))
        csv_form.addRow("CRS das coordenadas do CSV:", self.crs_csv)

        v.addLayout(csv_form)
        return group

    def _build_start_group(self):
        group = QGroupBox("Ponto de partida")
        v = QVBoxLayout(group)

        self.rb_start_selected = QRadioButton("Feição selecionada na camada")
        self.rb_start_manual = QRadioButton("Coordenada manual")
        self.rb_start_centroid = QRadioButton("Centróide do conjunto de pontos")
        self.rb_start_selected.setChecked(True)
        v.addWidget(self.rb_start_selected)
        v.addWidget(self.rb_start_manual)
        v.addWidget(self.rb_start_centroid)

        manual_form = QFormLayout()
        coord_row = QHBoxLayout()
        self.le_manual_x = QLineEdit()
        self.le_manual_x.setPlaceholderText("X / Longitude")
        self.le_manual_y = QLineEdit()
        self.le_manual_y.setPlaceholderText("Y / Latitude")
        coord_row.addWidget(self.le_manual_x)
        coord_row.addWidget(self.le_manual_y)
        manual_form.addRow("Coordenada:", coord_row)

        self.crs_manual = QgsProjectionSelectionWidget()
        self.crs_manual.setCrs(QgsCoordinateReferenceSystem("EPSG:4674"))
        manual_form.addRow("CRS da coordenada:", self.crs_manual)
        v.addLayout(manual_form)

        note = QLabel(
            "Ao usar coordenada manual ou centróide, um ponto de partida "
            "sintético é adicionado à camada de saída (marcado no campo "
            "'ponto_partida')."
        )
        note.setWordWrap(True)
        v.addWidget(note)

        return group

    def _build_distance_group(self):
        group = QGroupBox("Método de cálculo de distância")
        v = QVBoxLayout(group)

        self.rb_dist_straight = QRadioButton("Distância em linha reta (mais rápido, ignora ruas/quadras)")
        self.rb_dist_network = QRadioButton("Rede viária — segue as ruas (recomendado)")
        self.rb_dist_straight.setChecked(True)
        v.addWidget(self.rb_dist_straight)
        v.addWidget(self.rb_dist_network)

        network_form = QFormLayout()
        self.cbo_network_layer = QgsMapLayerComboBox()
        self.cbo_network_layer.setFilters(QgsMapLayerProxyModel.LineLayer)
        network_form.addRow("Camada de malha viária:", self.cbo_network_layer)
        v.addLayout(network_form)

        return group

    # --------------------------------------------------------------- sinais
    def _connect_signals(self):
        self.rb_input_layer.toggled.connect(self._update_enabled_states)
        self.rb_input_csv.toggled.connect(self._update_enabled_states)
        self.rb_start_manual.toggled.connect(self._update_enabled_states)
        self.rb_dist_network.toggled.connect(self._update_enabled_states)
        self.file_csv.fileChanged.connect(self._on_csv_file_changed)

    def _update_enabled_states(self):
        is_layer_mode = self.rb_input_layer.isChecked()
        self.cbo_input_layer.setEnabled(is_layer_mode)
        self.file_csv.setEnabled(not is_layer_mode)
        self.cbo_csv_x.setEnabled(not is_layer_mode)
        self.cbo_csv_y.setEnabled(not is_layer_mode)
        self.crs_csv.setEnabled(not is_layer_mode)

        # "Feição selecionada" só faz sentido quando a entrada já é uma
        # camada carregada no projeto.
        self.rb_start_selected.setEnabled(is_layer_mode)
        if not is_layer_mode and self.rb_start_selected.isChecked():
            self.rb_start_centroid.setChecked(True)

        is_manual_start = self.rb_start_manual.isChecked()
        self.le_manual_x.setEnabled(is_manual_start)
        self.le_manual_y.setEnabled(is_manual_start)
        self.crs_manual.setEnabled(is_manual_start)

        self.cbo_network_layer.setEnabled(self.rb_dist_network.isChecked())

    def _on_csv_file_changed(self, path):
        self.cbo_csv_x.clear()
        self.cbo_csv_y.clear()
        if not path:
            return
        try:
            header = read_csv_header(path)
        except Exception:
            return
        self.cbo_csv_x.addItems(header)
        self.cbo_csv_y.addItems(header)

    # ----------------------------------------------------------- validação
    def get_parameters(self):
        """Lê e valida os campos do diálogo, retornando um dict de parâmetros.

        Lança ValueError com mensagem em português caso algo esteja
        incompleto ou inconsistente.
        """
        params = {}

        if self.rb_input_layer.isChecked():
            layer = self.cbo_input_layer.currentLayer()
            if layer is None:
                raise ValueError("Selecione uma camada de pontos de entrada.")
            params["source_mode"] = "layer"
            params["layer"] = layer
        else:
            path = self.file_csv.filePath()
            if not path:
                raise ValueError("Selecione um arquivo CSV.")
            x_field = self.cbo_csv_x.currentText()
            y_field = self.cbo_csv_y.currentText()
            if not x_field or not y_field:
                raise ValueError("Selecione as colunas de X/Longitude e Y/Latitude do CSV.")
            params["source_mode"] = "csv"
            params["csv_path"] = path
            params["csv_x_field"] = x_field
            params["csv_y_field"] = y_field
            params["csv_crs"] = self.crs_csv.crs()

        if self.rb_start_selected.isChecked():
            params["start_mode"] = "selected_feature"
        elif self.rb_start_manual.isChecked():
            try:
                manual_x = float(self.le_manual_x.text().strip().replace(",", "."))
                manual_y = float(self.le_manual_y.text().strip().replace(",", "."))
            except ValueError as exc:
                raise ValueError("Coordenada manual do ponto de partida inválida.") from exc
            manual_crs = self.crs_manual.crs()
            if not manual_crs.isValid():
                raise ValueError("Selecione um CRS válido para a coordenada manual.")
            params["start_mode"] = "manual"
            params["manual_x"] = manual_x
            params["manual_y"] = manual_y
            params["manual_crs"] = manual_crs
        else:
            params["start_mode"] = "centroid"

        if self.rb_dist_straight.isChecked():
            params["distance_method"] = DISTANCE_STRAIGHT
            params["network_layer"] = None
        else:
            network_layer = self.cbo_network_layer.currentLayer()
            if network_layer is None:
                raise ValueError("Selecione a camada de malha viária para o método de rede viária.")
            params["distance_method"] = DISTANCE_NETWORK
            params["network_layer"] = network_layer

        return params
