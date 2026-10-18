"""Canvas: desenha pixel a pixel sobre um buffer de memória RGBA (framebuffer CPU).

Equivalente a src/canvas.zig. Todos os algoritmos (Bresenham para retas,
ponto médio para círculos, flood fill) são implementados à mão; o buffer
é mantido diretamente em memória e transferido para exibição via OpenGL/GLFW.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def offset(self, dx: int, dy: int) -> Point:
        return Point(self.x + dx, self.y + dy)


Color = tuple[int, int, int, int]  # (r, g, b, a)


class Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.buffer = bytearray(width * height * 4)
        self.draw_color: Color = (0, 0, 0, 255)
        self.is_drawing = False
        self.last_point: Point | None = None

    def clear(self, color: Color) -> None:
        self.buffer[:] = bytes(color) * (self.width * self.height)

    # ------------------------------------------------------------------
    # Traço livre (modo FREE)
    # ------------------------------------------------------------------
    def begin_stroke(self, point: Point) -> None:
        self.is_drawing = True
        self.last_point = point
        self.plot_pixel(point)

    def extend_stroke(self, point: Point) -> None:
        if not self.is_drawing:
            return

        if self.last_point is not None:
            self.draw_line(self.last_point, point)
        self.last_point = point

    def end_stroke(self) -> None:
        self.is_drawing = False
        self.last_point = None

    # ------------------------------------------------------------------
    # Primitivas
    # ------------------------------------------------------------------
    def draw_line(self, start: Point, end: Point) -> None:
        """Bresenham generalizado (funciona em todos os octantes)."""
        dx = abs(end.x - start.x)
        dy = -abs(end.y - start.y)
        step_x = 1 if start.x < end.x else -1
        step_y = 1 if start.y < end.y else -1

        err = dx + dy
        x, y = start.x, start.y
        w, h = self.width, self.height
        buf = self.buffer
        color_bytes = bytes(self.draw_color)

        while True:
            if 0 <= x < w and 0 <= y < h:
                idx = (y * w + x) * 4
                buf[idx : idx + 4] = color_bytes
            if x == end.x and y == end.y:
                break

            doubled_err = 2 * err
            if doubled_err >= dy:
                err += dy
                x += step_x
            if doubled_err <= dx:
                err += dx
                y += step_y

    def draw_circle(self, center: Point, radius: int) -> None:
        """Algoritmo do ponto médio (Bresenham para círculos)."""
        x = 0
        y = radius
        err = 3 - 2 * radius

        while x <= y:
            self._plot_circle_octants(center, x, y)

            if err > 0:
                err += 4 * (x - y) + 10
                y -= 1
            else:
                err += 4 * x + 6
            x += 1

    def draw_filled_circle(self, center: Point, radius: int) -> None:
        """Círculo preenchido usando o algoritmo do ponto médio com scanlines horizontais."""
        x = 0
        y = radius
        err = 3 - 2 * radius

        while x <= y:
            self._draw_hline(center.x - x, center.x + x, center.y + y)
            self._draw_hline(center.x - x, center.x + x, center.y - y)
            self._draw_hline(center.x - y, center.x + y, center.y + x)
            self._draw_hline(center.x - y, center.x + y, center.y - x)

            if err > 0:
                err += 4 * (x - y) + 10
                y -= 1
            else:
                err += 4 * x + 6
            x += 1

    def draw_rectangle(self, start: Point, end: Point) -> None:
        """Desenha um retângulo (ou quadrado) conectando 4 retas via Bresenham."""
        q2 = Point(start.x, end.y)
        q3 = Point(end.x, start.y)
        self.draw_line(start, q2)
        self.draw_line(start, q3)
        self.draw_line(end, q2)
        self.draw_line(end, q3)

    def draw_filled_rectangle(self, start: Point, end: Point) -> None:
        """Desenha um retângulo preenchido varrendo scanlines horizontais."""
        y_min = max(0, min(start.y, end.y))
        y_max = min(self.height - 1, max(start.y, end.y))
        for y in range(y_min, y_max + 1):
            self._draw_hline(start.x, end.x, y)

    def _draw_hline(self, x0: int, x1: int, y: int) -> None:
        if not (0 <= y < self.height):
            return
        if x0 > x1:
            x0, x1 = x1, x0
        x0 = max(0, x0)
        x1 = min(self.width - 1, x1)
        if x0 > x1:
            return
        span = x1 - x0 + 1
        start_idx = (y * self.width + x0) * 4
        self.buffer[start_idx : start_idx + span * 4] = bytes(self.draw_color) * span

    draw_square = draw_rectangle

    # ------------------------------------------------------------------
    # Preenchimento
    # ------------------------------------------------------------------
    def flood_fill(self, source: Point) -> None:
        if not self._in_bounds(source):
            return

        target = self._read_pixel(source)
        if target == self.draw_color:
            return

        self._dfs(source, target)

    def _dfs(self, source: Point, target: Color) -> None:
        """DFS com pilha explícita sobre o buffer de pixels.

        A versão em Zig é recursiva; em Python isso estoura o limite de
        recursão (~1000 chamadas) logo numa área pequena, então usamos uma
        pilha. A ordem de visita (direita, esquerda, baixo, cima) é a mesma.
        """
        buf = self.buffer
        w = self.width
        h = self.height
        color_bytes = bytes(self.draw_color)
        target_bytes = bytes(target)

        stack = [(source.x, source.y)]
        while stack:
            x, y = stack.pop()
            if not (0 <= x < w and 0 <= y < h):
                continue

            idx = (y * w + x) * 4
            if buf[idx : idx + 4] != target_bytes:
                continue

            buf[idx : idx + 4] = color_bytes

            # Empilhados ao contrário para que o primeiro a sair seja
            # x + 1, igual à ordem das chamadas recursivas no original.
            stack.append((x, y - 1))
            stack.append((x, y + 1))
            stack.append((x - 1, y))
            stack.append((x + 1, y))

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def plot_pixel(self, point: Point) -> None:
        if not self._in_bounds(point):
            return
        idx = (point.y * self.width + point.x) * 4
        self.buffer[idx : idx + 4] = bytes(self.draw_color)

    def _read_pixel(self, point: Point) -> Color:
        idx = (point.y * self.width + point.x) * 4
        return (self.buffer[idx], self.buffer[idx + 1], self.buffer[idx + 2], self.buffer[idx + 3])

    def _in_bounds(self, point: Point) -> bool:
        return 0 <= point.x < self.width and 0 <= point.y < self.height

    def _plot_circle_octants(self, center: Point, x: int, y: int) -> None:
        offsets = (
            (x, y), (-x, y), (x, -y), (-x, -y),
            (y, x), (-y, x), (y, -x), (-y, -x),
        )
        for ox, oy in offsets:
            self.plot_pixel(center.offset(ox, oy))
