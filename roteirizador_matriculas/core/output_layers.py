"""Construção das camadas de saída: pontos com ordem de visita e rota."""

from qgis.core import QgsFeature, QgsField, QgsFields, QgsGeometry, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant


def build_output_layers(points, order, matrix, segments, source_fields, source_attributes, crs, name_prefix="Sequencia_Visita"):
    """Monta as camadas de pontos (com ordem/distâncias) e de rota.

    `points`: lista de QgsPointXY (todas as matrículas + eventual ponto de
        partida sintético), no CRS `crs`.
    `order`: sequência de visita (índices em `points`); `order[0]` é o
        ponto de partida.
    `matrix`: matriz de distâncias (metros) usada no cálculo da rota.
    `segments`: trechos de geometria (lista de QgsPointXY) entre paradas
        consecutivas de `order`, na mesma ordem.
    `source_fields`: QgsFields originais dos pontos de entrada (pode ser
        vazio, por exemplo para o ponto de partida sintético).
    `source_attributes`: lista paralela a `points` com os atributos
        originais de cada ponto (listas vazias quando não há atributo).

    Retorna (points_layer, route_layer), ambas camadas em memória prontas
    para serem adicionadas ao projeto.
    """
    fields = QgsFields()
    for f in source_fields:
        fields.append(f)
    fields.append(QgsField("ordem_visita", QVariant.Int))
    fields.append(QgsField("ponto_partida", QVariant.Bool))
    fields.append(QgsField("dist_prox_m", QVariant.Double))
    fields.append(QgsField("dist_acum_m", QVariant.Double))

    points_layer = QgsVectorLayer(f"Point?crs={crs.authid()}", f"{name_prefix}_Pontos", "memory")
    provider = points_layer.dataProvider()
    provider.addAttributes(fields)
    points_layer.updateFields()

    out_features = []
    acumulado = 0.0
    for seq, idx in enumerate(order):
        if seq > 0:
            acumulado += matrix[order[seq - 1]][order[seq]]
        dist_prox = matrix[order[seq]][order[seq + 1]] if seq < len(order) - 1 else 0.0

        feat = QgsFeature(fields)
        feat.setGeometry(QgsGeometry.fromPointXY(points[idx]))
        base_attrs = list(source_attributes[idx]) if source_attributes and source_attributes[idx] else [None] * len(source_fields)
        feat.setAttributes(base_attrs + [seq + 1, seq == 0, dist_prox, acumulado])
        out_features.append(feat)
    provider.addFeatures(out_features)
    points_layer.updateExtents()

    route_fields = QgsFields()
    route_fields.append(QgsField("trecho", QVariant.Int))
    route_fields.append(QgsField("origem_ordem", QVariant.Int))
    route_fields.append(QgsField("destino_ordem", QVariant.Int))
    route_fields.append(QgsField("distancia_m", QVariant.Double))

    route_layer = QgsVectorLayer(f"LineString?crs={crs.authid()}", f"{name_prefix}_Rota", "memory")
    route_provider = route_layer.dataProvider()
    route_provider.addAttributes(route_fields)
    route_layer.updateFields()

    route_features = []
    for i, seg in enumerate(segments):
        feat = QgsFeature(route_fields)
        feat.setGeometry(QgsGeometry.fromPolylineXY(seg))
        feat.setAttributes([i + 1, i + 1, i + 2, matrix[order[i]][order[i + 1]]])
        route_features.append(feat)
    route_provider.addFeatures(route_features)
    route_layer.updateExtents()

    return points_layer, route_layer
