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
    glColor3ub,
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

from canvas import Canvas, Color, Point
from sidebar import Sidebar


class DrawState(Enum):
    FREE = auto()
    LINE = auto()
    RECTANGLE = auto()
    FILLED_RECTANGLE = auto()
    CIRCLE = auto()
    FILLED_CIRCLE = auto()
    TRIANGLE = auto()
    FILL = auto()
    CLIPPING = auto()
    SELECTING = auto()


SHAPE_STATES = (
    DrawState.LINE,
    DrawState.CIRCLE,
    DrawState.FILLED_CIRCLE,
    DrawState.RECTANGLE,
    DrawState.FILLED_RECTANGLE,
)

KEY_TO_STATE = {
    glfw.KEY_G: DrawState.FILL,
    glfw.KEY_1: DrawState.FREE,
    glfw.KEY_2: DrawState.LINE,
    glfw.KEY_3: DrawState.CIRCLE,
    glfw.KEY_4: DrawState.RECTANGLE,
    glfw.KEY_5: DrawState.FILLED_CIRCLE,
    glfw.KEY_6: DrawState.FILLED_RECTANGLE,
    glfw.KEY_R: DrawState.RECTANGLE,
}


class Core:
    def __init__(self, screen_width: int, screen_height: int, sidebar_width: int = 80) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.sidebar_width = sidebar_width
        self.window_width = self.sidebar_width + self.screen_width
        self.window_height = self.screen_height

        if not glfw.init():
            raise RuntimeError("Falha ao inicializar o GLFW.")

        glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)
        self.window = glfw.create_window(
            self.window_width, self.window_height, "ImCooked", None, None
        )
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Falha ao criar janela GLFW.")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

        self.canvas = Canvas(self.screen_width, self.screen_height)
        self.canvas.clear((255, 255, 255, 255))

        self.running = False
        self.mouse_pressed = False
        self.draw_state = DrawState.FREE
        self.line_start: Point | None = None
        self.pending_point: Point | None = None
        self.snapshot: bytearray | None = None

        self.sidebar = Sidebar(
            width=self.sidebar_width,
            height=self.screen_height,
            get_color=lambda: self.canvas.draw_color,
            set_color=self.set_draw_color,
        )
        self._setup_sidebar_buttons()
        self._setup_gl()
        self._setup_callbacks()

    def _setup_sidebar_buttons(self) -> None:
        self.sidebar.add_button("free", 10, lambda: self.set_draw_state(DrawState.FREE), lambda: self.draw_state == DrawState.FREE)
        self.sidebar.add_button("line", 50, lambda: self.set_draw_state(DrawState.LINE), lambda: self.draw_state == DrawState.LINE)
        self.sidebar.add_button("circle", 90, lambda: self.set_draw_state(DrawState.CIRCLE), lambda: self.draw_state == DrawState.CIRCLE)
        self.sidebar.add_button("filled_circle", 130, lambda: self.set_draw_state(DrawState.FILLED_CIRCLE), lambda: self.draw_state == DrawState.FILLED_CIRCLE)
        self.sidebar.add_button("rect", 170, lambda: self.set_draw_state(DrawState.RECTANGLE), lambda: self.draw_state == DrawState.RECTANGLE)
        self.sidebar.add_button("filled_rect", 210, lambda: self.set_draw_state(DrawState.FILLED_RECTANGLE), lambda: self.draw_state == DrawState.FILLED_RECTANGLE)
        self.sidebar.add_button("fill", 250, lambda: self.set_draw_state(DrawState.FILL), lambda: self.draw_state == DrawState.FILL)
        self.sidebar.add_button("clear", 290, self.clear_canvas)
        self.sidebar.add_button("quit", 330, self.quit)

    def _setup_gl(self) -> None:
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
            self.canvas.buffer,
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
    # Ações e Eventos
    # ------------------------------------------------------------------
    def _on_key(self, window, key: int, scancode: int, action: int, mods: int) -> None:
        if action == glfw.PRESS:
            if key in (glfw.KEY_Q, glfw.KEY_ESCAPE):
                self.quit()
            elif key == glfw.KEY_C:
                self.clear_canvas()
            elif key in KEY_TO_STATE:
                self.set_draw_state(KEY_TO_STATE[key])

    def set_draw_state(self, state: DrawState) -> None:
        if self.snapshot is not None:
            self.canvas.buffer[:] = self.snapshot
            self.snapshot = None
        self.draw_state = state
        self.line_start = None
        self.pending_point = None
        self.canvas.end_stroke()

    def set_draw_color(self, color: Color) -> None:
        self.canvas.draw_color = color

    def clear_canvas(self) -> None:
        self.snapshot = None
        self.line_start = None
        self.pending_point = None
        self.canvas.end_stroke()
        self.canvas.clear((255, 255, 255, 255))

    def quit(self) -> None:
        if self.snapshot is not None:
            self.canvas.buffer[:] = self.snapshot
            self.snapshot = None
            self.line_start = None
            self.pending_point = None
        self.running = False
        if self.window is not None:
            glfw.set_window_should_close(self.window, True)

    def _on_mouse_button(self, window, button: int, action: int, mods: int) -> None:
        if button != glfw.MOUSE_BUTTON_LEFT:
            return

        x, y = glfw.get_cursor_pos(window)

        if action == glfw.PRESS:
            if x < self.sidebar_width:
                self.sidebar.handle_click(int(x), int(y))
                return

            point = Point(int(x) - self.sidebar_width, int(y))
            self.mouse_pressed = True
            if self.draw_state == DrawState.FREE:
                self.canvas.begin_stroke(point)
            elif self.draw_state in SHAPE_STATES:
                self.line_start = point
                self.pending_point = None
                self.snapshot = bytearray(self.canvas.buffer)
            elif self.draw_state == DrawState.FILL:
                self.canvas.flood_fill(point)
        elif action == glfw.RELEASE and self.mouse_pressed:
            point = Point(int(x) - self.sidebar_width, int(y))
            self.mouse_pressed = False
            if self.draw_state == DrawState.FREE:
                self.canvas.end_stroke()
            elif (
                self.draw_state in SHAPE_STATES
                and self.line_start is not None
                and self.snapshot is not None
            ):
                self.canvas.buffer[:] = self.snapshot
                target_point = self._get_effective_endpoint(self.line_start, point)
                self._draw_shape(self.line_start, target_point)
                self.line_start = None
                self.pending_point = None
                self.snapshot = None

    def _on_cursor_pos(self, window, xpos: float, ypos: float) -> None:
        if not self.mouse_pressed:
            return

        point = Point(int(xpos) - self.sidebar_width, int(ypos))
        if self.draw_state == DrawState.FREE:
            self.canvas.extend_stroke(point)
        elif (
            self.draw_state in SHAPE_STATES
            and self.line_start is not None
            and self.snapshot is not None
        ):
            self.pending_point = point

    def _get_effective_endpoint(self, start: Point, current: Point) -> Point:
        """Permite que o retângulo seja livre por padrão, ou travado em proporção 1:1
        (quadrado perfeito) ao segurar a tecla Shift."""
        if self.draw_state in (DrawState.RECTANGLE, DrawState.FILLED_RECTANGLE):
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
        elif self.draw_state == DrawState.FILLED_CIRCLE:
            self.canvas.draw_filled_circle(start, calculate_radius(start, end))
        elif self.draw_state == DrawState.RECTANGLE:
            self.canvas.draw_rectangle(start, end)
        elif self.draw_state == DrawState.FILLED_RECTANGLE:
            self.canvas.draw_filled_rectangle(start, end)

    # ------------------------------------------------------------------
    # Renderização e Loop principal
    # ------------------------------------------------------------------
    def _render_canvas(self, viewport_x: int, viewport_y: int, viewport_w: int, viewport_h: int) -> None:
        glViewport(viewport_x, viewport_y, viewport_w, viewport_h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.screen_width, self.screen_height, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glEnable(GL_TEXTURE_2D)
        glColor3ub(255, 255, 255)

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
            self.canvas.buffer,
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

    def render(self) -> None:
        if (
            self.pending_point is not None
            and self.line_start is not None
            and self.snapshot is not None
        ):
            self.canvas.buffer[:] = self.snapshot
            target_point = self._get_effective_endpoint(self.line_start, self.pending_point)
            self._draw_shape(self.line_start, target_point)
            self.pending_point = None

        glClear(GL_COLOR_BUFFER_BIT)

        fb_w, fb_h = glfw.get_framebuffer_size(self.window)
        sidebar_fb_w = int(fb_w * (self.sidebar_width / self.window_width))
        canvas_fb_w = fb_w - sidebar_fb_w

        # Renderiza a Sidebar e o Canvas em viewports/contextos de projeção independentes
        self.sidebar.render(0, 0, sidebar_fb_w, fb_h)
        self._render_canvas(sidebar_fb_w, 0, canvas_fb_w, fb_h)

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

