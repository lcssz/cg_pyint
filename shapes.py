"""Formas geométricas (equivalente a src/shapes.zig).

Cada forma guarda seus vértices em float, para que rotações e escalas
repetidas não acumulem erro de arredondamento; só ao desenhar viram inteiros.
"""

from __future__ import annotations

import math

from canvas import Canvas, Color, Point


def _dist_to_segment(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / length2))
    return math.hypot(px - (a[0] + t * dx), py - (a[1] + t * dy))


class Shape:
    closed = False

    def __init__(self, points: list[Point], color: Color, thickness: int = 1, filled: bool = False) -> None:
        self.coords = [(float(p.x), float(p.y)) for p in points]
        self.color = color
        self.thickness = thickness
        self.filled = filled

    def vertices(self) -> list[Point]:
        return [Point(round(x), round(y)) for x, y in self.coords]

    def pivot(self) -> tuple[float, float]:
        n = len(self.coords)
        return sum(x for x, _ in self.coords) / n, sum(y for _, y in self.coords) / n

    def bounds(self) -> tuple[int, int, int, int]:
        v = self.vertices()
        return min(p.x for p in v), min(p.y for p in v), max(p.x for p in v), max(p.y for p in v)

    # ------------------------------------------------------------------
    # Transformações geométricas (em torno do pivô da forma)
    # ------------------------------------------------------------------
    def translate(self, dx: float, dy: float) -> None:
        self.coords = [(x + dx, y + dy) for x, y in self.coords]

    def rotate(self, angle: float) -> None:
        px, py = self.pivot()
        c, s = math.cos(angle), math.sin(angle)
        self.coords = [
            (px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c)
            for x, y in self.coords
        ]

    def scale(self, factor: float) -> None:
        px, py = self.pivot()
        self.coords = [(px + (x - px) * factor, py + (y - py) * factor) for x, y in self.coords]

    # ------------------------------------------------------------------
    # Seleção e desenho
    # ------------------------------------------------------------------
    def contains(self, point: Point) -> bool:
        """Clique perto do contorno (tolerância em pixels)."""
        tol = max(4, self.thickness)
        ends = self.coords[1:] + (self.coords[:1] if self.closed else [])
        return any(_dist_to_segment(point.x, point.y, a, b) <= tol for a, b in zip(self.coords, ends))

    def draw(self, canvas: Canvas) -> None:
        color, thickness = canvas.draw_color, canvas.thickness
        canvas.draw_color, canvas.thickness = self.color, self.thickness
        self._draw(canvas)
        canvas.draw_color, canvas.thickness = color, thickness

    def _draw(self, canvas: Canvas) -> None:
        raise NotImplementedError


class Line(Shape):
    def _draw(self, canvas: Canvas) -> None:
        canvas.draw_line(*self.vertices())


class Polygon(Shape):
    """Retângulos e triângulos: ao girar, o retângulo deixa de ser alinhado aos eixos."""

    closed = True

    def contains(self, point: Point) -> bool:
        if super().contains(point):
            return True
        if not self.filled:
            return False
        inside = False
        for (x0, y0), (x1, y1) in zip(self.coords, self.coords[1:] + self.coords[:1]):
            if (y0 > point.y) != (y1 > point.y) and point.x < x0 + (point.y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
        return inside

    def _draw(self, canvas: Canvas) -> None:
        if self.filled:
            canvas.draw_filled_polygon(self.vertices())
        else:
            canvas.draw_polygon(self.vertices())


class Circle(Shape):
    """Dois pontos: o centro e um ponto da borda (o raio é a distância entre eles)."""

    def radius(self) -> int:
        (cx, cy), (rx, ry) = self.coords
        return int(math.hypot(rx - cx, ry - cy))

    def pivot(self) -> tuple[float, float]:
        return self.coords[0]

    def bounds(self) -> tuple[int, int, int, int]:
        c, r = self.vertices()[0], self.radius()
        return c.x - r, c.y - r, c.x + r, c.y + r

    def contains(self, point: Point) -> bool:
        d = math.hypot(point.x - self.coords[0][0], point.y - self.coords[0][1])
        return abs(d - self.radius()) <= max(4, self.thickness) or (self.filled and d <= self.radius())

    def _draw(self, canvas: Canvas) -> None:
        center = self.vertices()[0]
        if self.filled:
            canvas.draw_filled_circle(center, self.radius())
        else:
            canvas.draw_circle(center, self.radius())
