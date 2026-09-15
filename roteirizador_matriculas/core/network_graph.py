"""Construção de grafo de rede viária e cálculo de menor caminho.

Usa a API de análise de redes do QGIS (qgis.analysis) para snapar os
pontos de entrada na malha viária, calcular a matriz de distâncias de
rede (via Dijkstra) e reconstruir a geometria real do caminho percorrido
entre duas paradas.
"""

import math

from qgis.analysis import (
    QgsGraphAnalyzer,
    QgsGraphBuilder,
    QgsNetworkDistanceStrategy,
    QgsVectorLayerDirector,
)

UNREACHABLE = math.inf


def build_network_graph(network_layer, points, crs):
    """Constrói o grafo a partir de `network_layer` e snapa `points` nele.

    Retorna (graph, vertex_indices), em que `vertex_indices[k]` é o índice
    do vértice do grafo mais próximo de `points[k]`.
    """
    director = QgsVectorLayerDirector(
        network_layer,
        -1,
        "",
        "",
        "",
        QgsVectorLayerDirector.DirectionBoth,
    )
    strategy = QgsNetworkDistanceStrategy()
    director.addStrategy(strategy)

    builder = QgsGraphBuilder(crs)
    tied_points = director.makeGraph(builder, points)
    graph = builder.graph()

    vertex_indices = [graph.findVertex(tp) for tp in tied_points]
    return graph, vertex_indices


def build_distance_matrix_network(graph, vertex_indices):
    """Roda Dijkstra a partir de cada ponto e monta a matriz de distâncias.

    Retorna (matrix, trees). `trees[i]` é a árvore de predecessores do
    Dijkstra calculada a partir de `vertex_indices[i]`, reaproveitada
    depois para reconstruir a geometria do caminho percorrido.
    Pares sem caminho na rede recebem distância `UNREACHABLE`.
    """
    n = len(vertex_indices)
    matrix = [[0.0] * n for _ in range(n)]
    trees = []
    for i, start_vidx in enumerate(vertex_indices):
        tree, costs = QgsGraphAnalyzer.dijkstra(graph, start_vidx, 0)
        trees.append(tree)
        for j, end_vidx in enumerate(vertex_indices):
            if i == j or end_vidx == start_vidx:
                matrix[i][j] = 0.0
            elif tree[end_vidx] == -1:
                matrix[i][j] = UNREACHABLE
            else:
                matrix[i][j] = costs[end_vidx]
    return matrix, trees


def reconstruct_network_path(graph, tree, start_vidx, end_vidx):
    """Reconstrói a geometria do menor caminho entre dois vértices do grafo.

    Percorre `tree` (árvore de predecessores do Dijkstra a partir de
    `start_vidx`) de `end_vidx` até `start_vidx`, retornando a lista de
    QgsPointXY do caminho na ordem correta (início -> fim). Retorna None
    se não houver caminho.
    """
    if start_vidx == end_vidx:
        return [graph.vertex(start_vidx).point()]

    path_points = []
    current = end_vidx
    visited = set()
    while current != start_vidx:
        if current in visited:
            return None
        visited.add(current)
        edge_id = tree[current]
        if edge_id == -1:
            return None
        edge = graph.edge(edge_id)
        v1, v2 = edge.fromVertex(), edge.toVertex()
        prev = v1 if v2 == current else v2
        path_points.append(graph.vertex(current).point())
        current = prev

    path_points.append(graph.vertex(start_vidx).point())
    path_points.reverse()
    return path_points
