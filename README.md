# Roteirizador de Matrículas — plugin QGIS

Plugin para QGIS que sequencia visitas/vistorias entre matrículas
georreferenciadas, gerando a ordem de visita mais eficiente a partir de um
ponto de partida. Suporta dois métodos de cálculo de distância, escolhidos
no próprio diálogo do plugin:

- **Linha reta**: mais rápido, ignora a malha viária.
- **Rede viária**: calcula o menor caminho real pelas ruas (evita que o
  agente de campo "pule" entre quadras sem seguir um caminho existente).

## Funcionalidades

- Entrada de matrículas por camada vetorial de pontos já carregada no QGIS
  **ou** por arquivo CSV com colunas de coordenadas (X/Longitude e
  Y/Latitude configuráveis).
- Ponto de partida definido por: feição selecionada na camada, coordenada
  digitada manualmente, ou centróide do conjunto de pontos.
- Sequenciamento pelo heurístico do vizinho mais próximo, refinado com
  2-opt.
- Saída: camada de pontos com os campos `ordem_visita`, `ponto_partida`,
  `dist_prox_m` (distância até a próxima parada) e `dist_acum_m` (distância
  acumulada), além de uma camada de linha com a rota resultante (segmento
  reto ou geometria real da rede viária, dependendo do método escolhido).

## Instalação (manual, para desenvolvimento/testes)

1. Localize a pasta de plugins do seu perfil QGIS:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Copie (ou crie um link simbólico para) a pasta `roteirizador_matriculas/`
   deste repositório dentro da pasta de plugins acima.
3. Abra o QGIS, vá em **Complementos → Gerenciar e Instalar Complementos →
   Instalados** e habilite "Roteirizador de Matrículas".
4. Um ícone será adicionado à barra de ferramentas e uma entrada no menu
   **Complementos**.

## Uso

1. Carregue no projeto a camada de pontos das matrículas (ou tenha o CSV
   com as coordenadas em mãos) e, se for usar o método de rede viária,
   carregue também a camada de linhas da malha viária.
2. Abra o plugin (ícone da barra de ferramentas ou menu Complementos).
3. Escolha a entrada (camada existente ou CSV), o ponto de partida e o
   método de cálculo de distância.
4. Clique em OK. Duas novas camadas serão adicionadas ao projeto: os
   pontos com a ordem de visita e a rota resultante.

## Observações e limitações da v0.1

- No método de rede viária, a malha precisa estar topologicamente
  conectada nos cruzamentos (ruas que se cruzam devem compartilhar um
  vértice). Malhas com falhas de topologia podem gerar erro de "sem
  caminho entre pontos" ou resultados inesperados.
- O cálculo de rota é um heurístico (vizinho mais próximo + 2-opt), não
  uma solução exata de TSP — adequado para o volume típico de matrículas
  de uma rotina de campo, mas não garante o ótimo global para conjuntos
  muito grandes.
- Não há dependência de serviços externos (OSRM, Google Directions etc.):
  todo o cálculo é feito localmente com a API de análise de redes do
  próprio QGIS.

## Estrutura do código

```
roteirizador_matriculas/
├── __init__.py                 # classFactory
├── metadata.txt                # metadados do plugin
├── roteirizador_matriculas.py  # classe principal do plugin (initGui/run)
├── roteirizador_dialog.py      # diálogo (entrada, ponto de partida, método)
├── icons/icon.svg
└── core/
    ├── algorithms.py           # vizinho mais próximo + 2-opt (puro Python)
    ├── distances.py            # matriz de distância em linha reta
    ├── network_graph.py        # grafo de rede viária + Dijkstra + geometria
    ├── csv_loader.py           # carregamento de CSV como camada de pontos
    ├── routing_service.py      # orquestrador (compute_route)
    └── output_layers.py        # construção das camadas de saída
```
