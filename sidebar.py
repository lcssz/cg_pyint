"""Sidebar: painel lateral simples renderizado em um viewport OpenGL separado."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from OpenGL.GL import (
    GL_LINES,
    GL_LINE_LOOP,
    GL_LINE_STRIP,
    GL_MODELVIEW,
    GL_POLYGON,
    GL_PROJECTION,
    GL_QUADS,
    GL_TEXTURE_2D,
    glBegin,
    glColor3ub,
    glDisable,
    glEnd,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glVertex2f,
    glViewport,
)

from canvas import Color


@dataclass
class Button:
    x: int
    y: int
    w: int
    h: int
    icon: str
    on_click: Callable[[], None]
    is_active: Callable[[], bool] | None = None

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass
class ColorBox:
    x: int
    y: int
    w: int
    h: int
    color: Color

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


class Sidebar:
    def __init__(
        self,
        width: int,
        height: int,
        get_color: Callable[[], Color],
        set_color: Callable[[Color], None],
    ) -> None:
        self.width = width
        self.height = height
        self.get_color = get_color
        self.set_color = set_color
        self.buttons: list[Button] = []
        self.colors: list[ColorBox] = []
        self._init_colors()

    def _init_colors(self) -> None:
        palette: list[Color] = [
            (0, 0, 0, 255),        # Preto
            (255, 255, 255, 255),  # Branco
            (220, 38, 38, 255),    # Vermelho
            (22, 163, 74, 255),    # Verde
            (37, 99, 235, 255),    # Azul
            (234, 179, 8, 255),    # Amarelo
            (0, 255, 255, 255),    # Ciano
            (255, 0, 255, 255),    # Magenta
        ]
        y = 310
        for i, c in enumerate(palette):
            col = i % 2
            row = i // 2
            self.colors.append(ColorBox(10 + col * 32, y + row * 32, 26, 26, c))

    def add_button(
        self,
        icon: str,
        x: int,
        y: int,
        on_click: Callable[[], None],
        is_active: Callable[[], bool] | None = None,
        w: int = 30,
        h: int = 30,
    ) -> None:
        self.buttons.append(Button(x, y, w, h, icon, on_click, is_active))

    def handle_click(self, x: int, y: int) -> None:
        for btn in self.buttons:
            if btn.contains(x, y):
                btn.on_click()
                return
        for box in self.colors:
            if box.contains(x, y):
                self.set_color(box.color)
                return

    def render(self, vx: int, vy: int, vw: int, vh: int) -> None:
        glViewport(vx, vy, vw, vh)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_TEXTURE_2D)

        # Fundo cinza simples
        self._rect(0, 0, self.width, self.height, (200, 200, 200))

        for btn in self.buttons:
            active = btn.is_active() if btn.is_active else False
            bg = (120, 160, 230) if active else (160, 160, 160)
            self._rect(btn.x, btn.y, btn.w, btn.h, bg)
            self._outline(btn.x, btn.y, btn.w, btn.h, (50, 50, 50))
            self._draw_icon(btn.icon, btn.x + btn.w // 2, btn.y + btn.h // 2)

        current = self.get_color()
        for box in self.colors:
            self._rect(box.x, box.y, box.w, box.h, box.color[:3])
            border = (0, 0, 0) if box.color == current else (100, 100, 100)
            self._outline(box.x, box.y, box.w, box.h, border)

    def _rect(self, x: int, y: int, w: int, h: int, c: tuple[int, int, int]) -> None:
        glColor3ub(*c)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x, y + h)
        glEnd()

    def _outline(self, x: int, y: int, w: int, h: int, c: tuple[int, int, int]) -> None:
        glColor3ub(*c)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x, y + h)
        glEnd()

    def _draw_icon(self, icon: str, cx: int, cy: int) -> None:
        glColor3ub(20, 20, 20)
        if icon == "free":
            glBegin(GL_LINE_STRIP)
            glVertex2f(cx - 10, cy + 5)
            glVertex2f(cx - 3, cy - 5)
            glVertex2f(cx + 3, cy + 5)
            glVertex2f(cx + 10, cy - 5)
            glEnd()
        elif icon == "line":
            glBegin(GL_LINES)
            glVertex2f(cx - 10, cy + 8)
            glVertex2f(cx + 10, cy - 8)
            glEnd()
        elif icon == "circle":
            glBegin(GL_LINE_LOOP)
            for i in range(16):
                a = 2 * math.pi * i / 16
                glVertex2f(cx + math.cos(a) * 9, cy + math.sin(a) * 9)
            glEnd()
        elif icon == "filled_circle":
            glBegin(GL_POLYGON)
            for i in range(16):
                a = 2 * math.pi * i / 16
                glVertex2f(cx + math.cos(a) * 9, cy + math.sin(a) * 9)
            glEnd()
        elif icon == "rect":
            self._outline(cx - 10, cy - 7, 20, 14, (20, 20, 20))
        elif icon == "filled_rect":
            self._rect(cx - 10, cy - 7, 20, 14, (20, 20, 20))
        elif icon == "fill":
            self._rect(cx - 8, cy - 8, 16, 16, self.get_color()[:3])
            self._outline(cx - 8, cy - 8, 16, 16, (20, 20, 20))
        elif icon == "clear":
            self._rect(cx - 10, cy - 7, 20, 14, (255, 255, 255))
            self._outline(cx - 10, cy - 7, 20, 14, (20, 20, 20))
        elif icon == "eraser":
            self._rect(cx - 9, cy - 5, 18, 10, (240, 170, 170))
            self._outline(cx - 9, cy - 5, 18, 10, (20, 20, 20))
        elif icon == "triangle":
            glBegin(GL_LINE_LOOP)
            glVertex2f(cx, cy - 8)
            glVertex2f(cx + 9, cy + 7)
            glVertex2f(cx - 9, cy + 7)
            glEnd()
        elif icon == "filled_triangle":
            glBegin(GL_POLYGON)
            glVertex2f(cx, cy - 8)
            glVertex2f(cx + 9, cy + 7)
            glVertex2f(cx - 9, cy + 7)
            glEnd()
        elif icon == "select":
            glBegin(GL_LINE_LOOP)
            glVertex2f(cx - 5, cy - 8)
            glVertex2f(cx - 5, cy + 7)
            glVertex2f(cx - 1, cy + 3)
            glVertex2f(cx + 5, cy + 3)
            glEnd()
        elif icon == "save":
            self._outline(cx - 8, cy - 8, 16, 16, (20, 20, 20))
            self._rect(cx - 4, cy - 8, 8, 5, (20, 20, 20))
            self._rect(cx - 5, cy + 1, 10, 7, (20, 20, 20))
        elif icon.startswith("thickness_"):
            n = int(icon.split("_")[1])
            self._rect(cx - 8, cy - n // 2, 16, n, (20, 20, 20))
        elif icon == "quit":
            glBegin(GL_LINES)
            glVertex2f(cx - 7, cy - 7)
            glVertex2f(cx + 7, cy + 7)
            glVertex2f(cx + 7, cy - 7)
            glVertex2f(cx - 7, cy + 7)
            glEnd()
