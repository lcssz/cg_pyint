# cg_paint (Python)

Port em Python do projeto `cg_paint` (originalmente em Zig + SDL3).

## Como rodar

```bash
pip install -r requirements.txt
python main.py
```

## Controles

| Tecla     | Ação                                      |
|-----------|-------------------------------------------|
| `1`       | Desenho livre (segure e arraste)          |
| `2`       | Reta (clique no início, clique no fim)    |
| `3`       | Círculo (clique no centro, clique na borda) |
| `4`       | Retângulo (clique em dois cantos opostos) |
| `g`       | Balde de tinta (flood fill)               |
| `q`/`Esc` | Sair                                      |

## Estrutura

| Zig               | Python       |
|-------------------|--------------|
| `src/main.zig`    | `main.py`    |
| `src/core.zig`    | `core.py`    |
| `src/canvas.zig`  | `canvas.py`  |
| `src/shapes.zig`  | `shapes.py`  |

Os algoritmos de rasterização (Bresenham, ponto médio, flood fill) continuam
implementados à mão; o pygame só é usado para abrir a janela, receber eventos
e ler/escrever pixels individuais (`get_at` / `set_at`).

## Diferenças em relação à versão Zig

- **Flood fill iterativo**: o DFS recursivo do original estouraria o limite de
  recursão do Python, então ele usa uma pilha explícita (mesma ordem de visita).
- **Biblioteca gráfica**: SDL3 foi trocado por pygame (que usa SDL por baixo).
