"""Core: janela, loop principal e tratamento de eventos usando GLFW e OpenGL.

Equivalente a src/core.zig.
"""

from __future__ import annotations

import math
from enum import Enum, auto

import glfw
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_MODELVIEW,
    GL_NEAREST,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGBA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_UNPACK_ALIGNMENT,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glClear,
    glDeleteTextures,
    glEnable,
    glEnd,
    glGenTextures,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glPixelStorei,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glTexSubImage2D,
    glVertex2f,
    glViewport,
)

from canvas import Canvas, Point


class DrawState(Enum):
    FREE = auto()
    LINE = auto()
    RECTANGLE = auto()
    CIRCLE = auto()
    TRIANGLE = auto()
    FILL = auto()
    CLIPPING = auto()
    SELECTING = auto()


KEY_TO_STATE = {
    glfw.KEY_G: DrawState.FILL,
    glfw.KEY_1: DrawState.FREE,
    glfw.KEY_2: DrawState.LINE,
    glfw.KEY_3: DrawState.CIRCLE,
    glfw.KEY_4: DrawState.RECTANGLE,
    glfw.KEY_R: DrawState.RECTANGLE,
}


class Core:
    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height

        if not glfw.init():
            raise RuntimeError("Falha ao inicializar o GLFW.")

        glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)
        self.window = glfw.create_window(screen_width, screen_height, "ImCooked", None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Falha ao criar janela GLFW.")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

        self.canvas = Canvas(screen_width, screen_height)
        self.canvas.clear((255, 255, 255, 255))

        self.running = False
        self.mouse_pressed = False
        self.draw_state = DrawState.FREE
        self.line_start: Point | None = None
        self.snapshot: bytearray | None = None

        self._setup_gl()
        self._setup_callbacks()

    def _setup_gl(self) -> None:
        fb_w, fb_h = glfw.get_framebuffer_size(self.window)
        glViewport(0, 0, fb_w, fb_h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        # Sistema de coordenadas 2D: (0, 0) no canto superior esquerdo
        glOrtho(0, self.screen_width, self.screen_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glEnable(GL_TEXTURE_2D)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            self.screen_width,
            self.screen_height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            bytes(self.canvas.buffer),
        )

    def _setup_callbacks(self) -> None:
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_cursor_pos_callback(self.window, self._on_cursor_pos)

    def deinit(self) -> None:
        if hasattr(self, "texture_id") and self.texture_id is not None:
            glDeleteTextures([self.texture_id])
            self.texture_id = None
        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
        glfw.terminate()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _on_key(self, window, key: int, scancode: int, action: int, mods: int) -> None:
        if action == glfw.PRESS:
            if key in (glfw.KEY_Q, glfw.KEY_ESCAPE):
                if self.snapshot is not None:
                    self.canvas.buffer[:] = self.snapshot
                    self.snapshot = None
                    self.line_start = None
                self.running = False
                glfw.set_window_should_close(window, True)
            elif key in KEY_TO_STATE:
                self.set_draw_state(KEY_TO_STATE[key])

    def set_draw_state(self, state: DrawState) -> None:
        if self.snapshot is not None:
            self.canvas.buffer[:] = self.snapshot
            self.snapshot = None
        self.draw_state = state
        self.line_start = None
        self.canvas.end_stroke()

    def _on_mouse_button(self, window, button: int, action: int, mods: int) -> None:
        if button != glfw.MOUSE_BUTTON_LEFT:
            return

        x, y = glfw.get_cursor_pos(window)
        point = Point(int(x), int(y))

        if action == glfw.PRESS:
            self.mouse_pressed = True
            if self.draw_state == DrawState.FREE:
                self.canvas.begin_stroke(point)
            elif self.draw_state in (DrawState.LINE, DrawState.CIRCLE, DrawState.RECTANGLE):
                self.line_start = point
                self.snapshot = bytearray(self.canvas.buffer)
            elif self.draw_state == DrawState.FILL:
                self.canvas.flood_fill(point)
        elif action == glfw.RELEASE:
            self.mouse_pressed = False
            if self.draw_state == DrawState.FREE:
                self.canvas.end_stroke()
            elif (
                self.draw_state in (DrawState.LINE, DrawState.CIRCLE, DrawState.RECTANGLE)
                and self.line_start is not None
                and self.snapshot is not None
            ):
                self.canvas.buffer[:] = self.snapshot
                target_point = self._get_effective_endpoint(self.line_start, point)
                self._draw_shape(self.line_start, target_point)
                self.line_start = None
                self.snapshot = None

    def _on_cursor_pos(self, window, xpos: float, ypos: float) -> None:
        if not self.mouse_pressed:
            return

        point = Point(int(xpos), int(ypos))
        if self.draw_state == DrawState.FREE:
            self.canvas.extend_stroke(point)
        elif (
            self.draw_state in (DrawState.LINE, DrawState.CIRCLE, DrawState.RECTANGLE)
            and self.line_start is not None
            and self.snapshot is not None
        ):
            self.canvas.buffer[:] = self.snapshot
            target_point = self._get_effective_endpoint(self.line_start, point)
            self._draw_shape(self.line_start, target_point)

    def _get_effective_endpoint(self, start: Point, current: Point) -> Point:
        """Permite que o retângulo seja livre por padrão, ou travado em proporção 1:1
        (quadrado perfeito) ao segurar a tecla Shift."""
        if self.draw_state == DrawState.RECTANGLE:
            shift_pressed = (
                glfw.get_key(self.window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
                or glfw.get_key(self.window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS
            )
            if shift_pressed:
                dx = current.x - start.x
                dy = current.y - start.y
                side = max(abs(dx), abs(dy))
                sign_x = 1 if dx >= 0 else -1
                sign_y = 1 if dy >= 0 else -1
                return Point(start.x + sign_x * side, start.y + sign_y * side)
        return current

    def _draw_shape(self, start: Point, end: Point) -> None:
        if self.draw_state == DrawState.LINE:
            self.canvas.draw_line(start, end)
        elif self.draw_state == DrawState.CIRCLE:
            self.canvas.draw_circle(start, calculate_radius(start, end))
        elif self.draw_state == DrawState.RECTANGLE:
            self.canvas.draw_rectangle(start, end)

    # ------------------------------------------------------------------
    # Renderização e Loop principal
    # ------------------------------------------------------------------
    def render(self) -> None:
        glClear(GL_COLOR_BUFFER_BIT)

        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            self.screen_width,
            self.screen_height,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            bytes(self.canvas.buffer),
        )

        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(0.0, 0.0)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(self.screen_width, 0.0)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(self.screen_width, self.screen_height)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(0.0, self.screen_height)
        glEnd()

        glfw.swap_buffers(self.window)

    def run(self) -> None:
        self.running = True
        while self.running and not glfw.window_should_close(self.window):
            glfw.poll_events()
            self.render()


def calculate_radius(start: Point, point: Point) -> int:
    dx = point.x - start.x
    dy = point.y - start.y
    return int(math.sqrt(dx * dx + dy * dy))
