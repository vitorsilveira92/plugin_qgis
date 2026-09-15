"""Algoritmos de sequenciamento de rota (TSP de caminho, com início fixo).

Módulo sem dependência do QGIS: recebe apenas uma matriz de distâncias
(lista de listas) e índices inteiros, o que facilita testes isolados.
"""

import math

UNREACHABLE = math.inf


def nearest_neighbor_order(matrix, start_index):
    """Constrói uma rota inicial pelo heurístico do vizinho mais próximo.

    Retorna a lista de índices na ordem de visita, sempre iniciando em
    `start_index`.
    """
    n = len(matrix)
    if n == 0:
        return []
    unvisited = set(range(n))
    unvisited.discard(start_index)
    order = [start_index]
    current = start_index
    while unvisited:
        nxt = min(unvisited, key=lambda j: matrix[current][j])
        order.append(nxt)
        unvisited.discard(nxt)
        current = nxt
    return order


def route_length(order, matrix):
    """Soma das distâncias entre paradas consecutivas da rota."""
    return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def two_opt(order, matrix, max_iterations=1000):
    """Refina a rota com o heurístico 2-opt, mantendo o primeiro ponto fixo.

    O primeiro elemento de `order` é o ponto de partida e nunca é
    realocado: apenas o restante da sequência é reordenado.
    """
    n = len(order)
    if n < 4:
        return order[:]

    best = order[:]
    improved = True
    iterations = 0
    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        for i in range(1, n - 2):
            a, b = best[i - 1], best[i]
            for j in range(i + 1, n - 1):
                c, d = best[j], best[j + 1]
                current_cost = matrix[a][b] + matrix[c][d]
                new_cost = matrix[a][c] + matrix[b][d]
                if new_cost + 1e-9 < current_cost:
                    best[i:j + 1] = reversed(best[i:j + 1])
                    improved = True
                    b = best[i]
    return best
