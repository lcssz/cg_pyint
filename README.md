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
| `1`       | Desenho livre (segure e arraste)          |
| `2`       | Reta (clique, segure e arraste)           |
| `3`       | Círculo (clique no centro, segure e arraste o raio) |
| `4` / `r` | Retângulo (clique, segure e arraste até o canto oposto; `Shift` trava em quadrado) |
| `g`       | Balde de tinta (flood fill)               |
| `c`       | Limpar tela                               |
| `q`/`Esc` | Sair                                      |

Todas as ferramentas, seletor de cores e ações também estão disponíveis clicando nos botões da **Sidebar** lateral.

## Estrutura

| Zig               | Python       |
|-------------------|--------------|
| `src/main.zig`    | `main.py`    |
| `src/core.zig`    | `core.py`    |
| `src/canvas.zig`  | `canvas.py`  |
| `src/shapes.zig`  | `shapes.py`  |
| *(Novo)*          | `sidebar.py` |

Os algoritmos de rasterização (Bresenham, ponto médio, flood fill) continuam
implementados à mão sobre um framebuffer CPU em memória (`bytearray` RGBA).
A `Sidebar` é renderizada em um `glViewport` e sistema de projeção OpenGL
separados ao lado do `Canvas`, garantindo isolamento total sem necessidade de
algoritmos de clipping para proteger a interface.

## Diferenças em relação à versão Zig

- **Flood fill iterativo**: o DFS recursivo do original estouraria o limite de
  recursão do Python, então ele usa uma pilha explícita (mesma ordem de visita).
- **Biblioteca gráfica**: SDL3 foi trocado por GLFW para gerenciamento de janelas e contexto gráfico OpenGL.
