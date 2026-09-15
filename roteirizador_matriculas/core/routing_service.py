"""Orquestração do cálculo de rota: escolhe o método de distância,
monta a matriz, sequencia as paradas e devolve as geometrias dos trechos.
"""

from .algorithms import nearest_neighbor_order, route_length, two_opt
from .distances import build_distance_matrix_straight
from .network_graph import build_distance_matrix_network, build_network_graph, reconstruct_network_path
from .network_graph import UNREACHABLE

DISTANCE_STRAIGHT = "straight"
DISTANCE_NETWORK = "network"


class RoutingError(Exception):
    """Erro de negócio ao calcular a rota (rede desconectada, etc.)."""


def compute_route(points, crs, start_index, method, network_layer=None):
    """Calcula a sequência de visita otimizada para `points`.

    `points`: lista de QgsPointXY, todos no CRS `crs`.
    `start_index`: índice (em `points`) do ponto de partida fixo.
    `method`: DISTANCE_STRAIGHT ou DISTANCE_NETWORK.
    `network_layer`: camada de linhas da malha viária, obrigatória quando
        `method == DISTANCE_NETWORK`.

    Retorna um dict com:
        order: lista de índices na ordem de visita (order[0] == start_index)
        matrix: matriz de distâncias (metros) usada no cálculo
        segments: lista de trechos (cada um uma lista de QgsPointXY) entre
            paradas consecutivas de `order`
        total_distance: distância total da rota (metros)
    """
    if len(points) < 2:
        raise RoutingError("São necessários ao menos 2 pontos para calcular uma rota.")

    if method == DISTANCE_STRAIGHT:
        matrix = build_distance_matrix_straight(points, crs)
        order = nearest_neighbor_order(matrix, start_index)
        order = two_opt(order, matrix)
        segments = [[points[order[i]], points[order[i + 1]]] for i in range(len(order) - 1)]

    elif method == DISTANCE_NETWORK:
        if network_layer is None:
            raise RoutingError("Método 'rede viária' selecionado, mas nenhuma camada de malha viária foi informada.")

        graph, vertex_indices = build_network_graph(network_layer, points, crs)
        matrix, trees = build_distance_matrix_network(graph, vertex_indices)

        order = nearest_neighbor_order(matrix, start_index)
        order = two_opt(order, matrix)

        segments = []
        for i in range(len(order) - 1):
            a, b = order[i], order[i + 1]
            if matrix[a][b] == UNREACHABLE:
                raise RoutingError(
                    f"Não há caminho pela malha viária entre os pontos de ordem {i + 1} e {i + 2}. "
                    "Verifique se a malha viária está topologicamente conectada (ruas sem "
                    "interseção nos cruzamentos costumam causar esse problema)."
                )
            path = reconstruct_network_path(graph, trees[a], vertex_indices[a], vertex_indices[b])
            if path is None:
                raise RoutingError(
                    f"Não foi possível reconstruir o trajeto pela malha viária entre os pontos "
                    f"de ordem {i + 1} e {i + 2}."
                )
            segments.append(path)

    else:
        raise RoutingError(f"Método de distância desconhecido: {method!r}")

    total = route_length(order, matrix)
    return {
        "order": order,
        "matrix": matrix,
        "segments": segments,
        "total_distance": total,
    }
