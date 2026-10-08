"""Canvas: desenha pixel a pixel sobre uma pygame.Surface.

Equivalente a src/canvas.zig. Todos os algoritmos (Bresenham para retas,
ponto médio para círculos, flood fill) são implementados à mão; o pygame
só é usado para ler/escrever pixels individuais.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def offset(self, dx: int, dy: int) -> "Point":
        return Point(self.x + dx, self.y + dy)


Color = tuple[int, int, int, int]  # (r, g, b, a)


class Canvas:
    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.draw_color: Color = (0, 0, 0, 255)
        self.is_drawing = False
        self.last_point: Point | None = None

    def clear(self, color: Color) -> None:
        self.surface.fill(color)

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

        while True:
            self.plot_pixel(Point(x, y))
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

    def draw_square(self, start: Point, end: Point) -> None:
        q2 = Point(start.x, end.y)
        q3 = Point(end.x, start.y)
        self.draw_line(start, q2)
        self.draw_line(start, q3)
        self.draw_line(end, q2)
        self.draw_line(end, q3)

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
        """DFS com pilha explícita.

        A versão em Zig é recursiva; em Python isso estoura o limite de
        recursão (~1000 chamadas) logo numa área pequena, então usamos uma
        pilha. A ordem de visita (direita, esquerda, baixo, cima) é a mesma.
        """
        # Atalhos locais: o laço roda uma vez por pixel, então evitar
        # criar objetos Point e buscar atributos faz bastante diferença.
        surface = self.surface
        get_at = surface.get_at
        set_at = surface.set_at
        color = self.draw_color
        w, h = surface.get_size()

        stack = [(source.x, source.y)]
        surface.lock()  # evita travar/destravar a cada get_at/set_at
        try:
            while stack:
                x, y = stack.pop()
                if not (0 <= x < w and 0 <= y < h):
                    continue
                if tuple(get_at((x, y))) != target:
                    continue

                set_at((x, y), color)

                # Empilhados ao contrário para que o primeiro a sair seja
                # x + 1, igual à ordem das chamadas recursivas no original.
                stack.append((x, y - 1))
                stack.append((x, y + 1))
                stack.append((x - 1, y))
                stack.append((x + 1, y))
        finally:
            surface.unlock()

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def plot_pixel(self, point: Point) -> None:
        if not self._in_bounds(point):
            return
        self.surface.set_at((point.x, point.y), self.draw_color)

    def _read_pixel(self, point: Point) -> Color:
        return tuple(self.surface.get_at((point.x, point.y)))  # type: ignore[return-value]

    def _in_bounds(self, point: Point) -> bool:
        w, h = self.surface.get_size()
        return 0 <= point.x < w and 0 <= point.y < h

    def _plot_circle_octants(self, center: Point, x: int, y: int) -> None:
        offsets = (
            (x, y), (-x, y), (x, -y), (-x, -y),
            (y, x), (-y, x), (y, -x), (-y, -x),
        )
        for ox, oy in offsets:
            self.plot_pixel(center.offset(ox, oy))
