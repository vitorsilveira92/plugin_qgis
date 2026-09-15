"""Carregamento de matrículas a partir de um arquivo CSV com coordenadas."""

import csv

from qgis.core import QgsFeature, QgsField, QgsFields, QgsGeometry, QgsPointXY, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant


class CsvLoadError(Exception):
    """Erro ao interpretar o arquivo CSV informado pelo usuário."""


def read_csv_header(path):
    """Retorna a lista de nomes de colunas (primeira linha) do CSV."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
    except OSError as exc:
        raise CsvLoadError(f"Não foi possível abrir o arquivo CSV: {exc}") from exc

    if not header:
        raise CsvLoadError("O arquivo CSV está vazio ou não possui cabeçalho.")
    return header


def load_points_from_csv(path, x_field, y_field, crs):
    """Lê o CSV e cria uma camada de pontos em memória.

    `x_field`/`y_field` são os nomes das colunas com a coordenada
    (longitude/X e latitude/Y, respectivamente) no CRS informado. As
    demais colunas do CSV são preservadas como atributos da camada.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            if x_field not in fieldnames or y_field not in fieldnames:
                raise CsvLoadError(
                    f"As colunas '{x_field}' e/ou '{y_field}' não foram encontradas no CSV."
                )

            qgs_fields = QgsFields()
            for name in fieldnames:
                qgs_fields.append(QgsField(name, QVariant.String))

            features = []
            for row_num, row in enumerate(reader, start=2):
                x_raw = (row.get(x_field) or "").strip()
                y_raw = (row.get(y_field) or "").strip()
                if not x_raw or not y_raw:
                    continue
                try:
                    x = float(x_raw.replace(",", "."))
                    y = float(y_raw.replace(",", "."))
                except ValueError as exc:
                    raise CsvLoadError(
                        f"Coordenada inválida na linha {row_num} do CSV "
                        f"({x_field}={x_raw!r}, {y_field}={y_raw!r})."
                    ) from exc

                feat = QgsFeature(qgs_fields)
                feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                feat.setAttributes([row.get(name, "") for name in fieldnames])
                features.append(feat)
    except OSError as exc:
        raise CsvLoadError(f"Não foi possível abrir o arquivo CSV: {exc}") from exc

    if not features:
        raise CsvLoadError("Nenhum ponto com coordenadas válidas foi encontrado no CSV.")

    layer = QgsVectorLayer(f"Point?crs={crs.authid()}", "matriculas_csv", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(qgs_fields)
    layer.updateFields()
    provider.addFeatures(features)
    layer.updateExtents()
    return layer
