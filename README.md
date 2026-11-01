# cg_paint (Python + GLFW)

Port em Python do projeto `cg_paint` (originalmente em Zig + SDL3) utilizando **GLFW** e **OpenGL**.

## Como rodar

```bash
pip install -r requirements.txt
python main.py
```

## Controles

| Tecla     | Ação                                      |
|-----------|-------------------------------------------|
| `1`       | Lápis (desenho livre, segure e arraste)   |
| `e`       | Borracha (pinta com a cor de fundo)       |
| `2`       | Reta (clique, segure e arraste)           |
| `3` / `5` | Círculo vazado / preenchido (centro e arraste o raio) |
| `4` / `r` / `6` | Retângulo vazado / preenchido (`Shift` trava em quadrado) |
| `7` / `8` | Triângulo vazado / preenchido (arraste a caixa que o contém) |
| `g`       | Balde de tinta (flood fill)               |
| `v`       | Selecionar forma (clique no contorno e arraste para mover) |
| `F1`/`F2`/`F3` | Espessura fina (1 px) / média (3 px) / grossa (5 px) |
| `s`       | Salvar o canvas como `paint_AAAAMMDD_HHMMSS.png` |
| `c`       | Limpar tela                               |
| `q`/`Esc` | Sair                                      |

Com uma forma selecionada (`v`): `←`/`→` giram 15°, `↑`/`↓` aumentam/diminuem a
escala, `Delete` apaga, e escolher outra cor ou espessura altera a forma.

Todas as ferramentas, seletor de cores (8 cores), espessuras e ações também estão
disponíveis clicando nos botões da **Sidebar** lateral.

## Formas editáveis

Retas, círculos, retângulos e triângulos viram objetos (`shapes.py`) guardados em
uma lista, redesenhados sobre a camada raster a cada alteração, o que permite mover,
girar e escalar. Elas deixam de ser editáveis (são gravadas no raster) quando você usa
lápis, borracha, balde ou limpa a tela.

## Estrutura

| Zig               | Python       |
|-------------------|--------------|
| `src/main.zig`    | `main.py`    |
| `src/core.zig`    | `core.py`    |
| `src/canvas.zig`  | `canvas.py`  |
| `src/shapes.zig`  | `shapes.py`  |
| *(Novo)*          | `sidebar.py` |

`shapes.py` contém `Line`, `Polygon` e `Circle`, com translação, rotação e escala.
`Canvas` expõe `put_pixel(x, y, cor)` e `get_pixel(x, y)`, base de todas as primitivas.

Os algoritmos de rasterização (Bresenham, ponto médio, flood fill) continuam
implementados à mão sobre um framebuffer CPU em memória (`bytearray` RGBA).
A `Sidebar` é renderizada em um `glViewport` e sistema de projeção OpenGL
separados ao lado do `Canvas`, garantindo isolamento total sem necessidade de
algoritmos de clipping para proteger a interface.

## Diferenças em relação à versão Zig

- **Flood fill iterativo**: o DFS recursivo do original estouraria o limite de
  recursão do Python, então ele usa uma pilha explícita (mesma ordem de visita).
- **Biblioteca gráfica**: SDL3 foi trocado por GLFW para gerenciamento de janelas e contexto gráfico OpenGL.
