"""Cálculo de matriz de distâncias em linha reta (sem malha viária)."""

from qgis.core import QgsDistanceArea, QgsProject


def build_distance_matrix_straight(points, crs):
    """Retorna matriz NxN (metros) de distância em linha reta entre `points`.

    Usa QgsDistanceArea, que calcula distância elipsoidal para CRS
    geográficos e distância planar para CRS projetados, de acordo com o
    `crs` informado.
    """
    da = QgsDistanceArea()
    da.setSourceCrs(crs, QgsProject.instance().transformContext())
    ellipsoid = QgsProject.instance().ellipsoid()
    da.setEllipsoid(ellipsoid if ellipsoid else "WGS84")

    n = len(points)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = da.measureLine(points[i], points[j])
            matrix[i][j] = matrix[j][i] = d
    return matrix
