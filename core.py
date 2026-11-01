"""Core: janela, loop principal e tratamento de eventos usando GLFW e OpenGL.

Equivalente a src/core.zig.
"""

from __future__ import annotations

import math
from datetime import datetime
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
from shapes import Circle, Line, Polygon, Shape
from sidebar import Sidebar


class DrawState(Enum):
    FREE = auto()
    ERASER = auto()
    LINE = auto()
    RECTANGLE = auto()
    FILLED_RECTANGLE = auto()
    CIRCLE = auto()
    FILLED_CIRCLE = auto()
    TRIANGLE = auto()
    FILLED_TRIANGLE = auto()
    FILL = auto()
    SELECTING = auto()


SHAPE_STATES = (
    DrawState.LINE,
    DrawState.CIRCLE,
    DrawState.FILLED_CIRCLE,
    DrawState.RECTANGLE,
    DrawState.FILLED_RECTANGLE,
    DrawState.TRIANGLE,
    DrawState.FILLED_TRIANGLE,
)

FILLED_STATES = (
    DrawState.FILLED_CIRCLE,
    DrawState.FILLED_RECTANGLE,
    DrawState.FILLED_TRIANGLE,
)

KEY_TO_STATE = {
    glfw.KEY_G: DrawState.FILL,
    glfw.KEY_1: DrawState.FREE,
    glfw.KEY_2: DrawState.LINE,
    glfw.KEY_3: DrawState.CIRCLE,
    glfw.KEY_4: DrawState.RECTANGLE,
    glfw.KEY_5: DrawState.FILLED_CIRCLE,
    glfw.KEY_6: DrawState.FILLED_RECTANGLE,
    glfw.KEY_7: DrawState.TRIANGLE,
    glfw.KEY_8: DrawState.FILLED_TRIANGLE,
    glfw.KEY_R: DrawState.RECTANGLE,
    glfw.KEY_E: DrawState.ERASER,
    glfw.KEY_V: DrawState.SELECTING,
}

THICKNESSES = (1, 3, 5)  # fino, médio, grosso
KEY_TO_THICKNESS = {glfw.KEY_F1: 1, glfw.KEY_F2: 3, glfw.KEY_F3: 5}

# Teclas que transformam a forma selecionada (aceitam repetição ao segurar).
TRANSFORM_KEYS = (
    glfw.KEY_LEFT,
    glfw.KEY_RIGHT,
    glfw.KEY_UP,
    glfw.KEY_DOWN,
    glfw.KEY_DELETE,
    glfw.KEY_BACKSPACE,
)
ROTATE_STEP = math.radians(15)
SCALE_STEP = 1.1
SELECTION_COLOR: Color = (0, 120, 255, 255)


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
        self.canvas.clear(self.canvas.background)

        self.running = False
        self.mouse_pressed = False
        self.draw_state = DrawState.FREE
        self.line_start: Point | None = None
        self.pending_point: Point | None = None
        # Formas ficam editáveis (lista) sobre `base` até o próximo desenho
        # livre/borracha/balde/limpar, que as grava no raster.
        self.shapes: list[Shape] = []
        self.base = bytearray(len(self.canvas.buffer))
        self.selected: Shape | None = None
        self.drag_last: Point | None = None
        self.dirty = False

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
        tools = (
            ("free", DrawState.FREE),
            ("eraser", DrawState.ERASER),
            ("line", DrawState.LINE),
            ("circle", DrawState.CIRCLE),
            ("filled_circle", DrawState.FILLED_CIRCLE),
            ("rect", DrawState.RECTANGLE),
            ("filled_rect", DrawState.FILLED_RECTANGLE),
            ("triangle", DrawState.TRIANGLE),
            ("filled_triangle", DrawState.FILLED_TRIANGLE),
            ("fill", DrawState.FILL),
            ("select", DrawState.SELECTING),
        )
        actions = (("clear", self.clear_canvas), ("save", self.save_canvas), ("quit", self.quit))

        # Grade de 2 colunas: ferramentas, depois ações, depois espessuras.
        for i, (icon, state) in enumerate(tools):
            self.sidebar.add_button(
                icon, 6 + (i % 2) * 38, 10 + (i // 2) * 36,
                lambda s=state: self.set_draw_state(s),
                lambda s=state: self.draw_state == s,
            )
        for j, (icon, action) in enumerate(actions, start=len(tools)):
            self.sidebar.add_button(icon, 6 + (j % 2) * 38, 10 + (j // 2) * 36, action)
        for k, t in enumerate(THICKNESSES):
            self.sidebar.add_button(
                f"thickness_{t}", 6 + k * 24, 268,
                lambda t=t: self.set_thickness(t),
                lambda t=t: self.canvas.thickness == t,
                w=22, h=24,
            )

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
        if key in TRANSFORM_KEYS and action in (glfw.PRESS, glfw.REPEAT):
            self._transform_selected(key)
        elif action == glfw.PRESS:
            if key in (glfw.KEY_Q, glfw.KEY_ESCAPE):
                self.quit()
            elif key == glfw.KEY_C:
                self.clear_canvas()
            elif key == glfw.KEY_S:
                self.save_canvas()
            elif key in KEY_TO_THICKNESS:
                self.set_thickness(KEY_TO_THICKNESS[key])
            elif key in KEY_TO_STATE:
                self.set_draw_state(KEY_TO_STATE[key])

    def set_draw_state(self, state: DrawState) -> None:
        # Descarta o preview em andamento e a seleção atual.
        self.selected = None
        if self.shapes or self.line_start is not None:
            self._redraw()
        self.draw_state = state
        self.mouse_pressed = False
        self.line_start = None
        self.pending_point = None
        self.drag_last = None
        self.canvas.end_stroke()
        self.canvas.eraser = state == DrawState.ERASER

    def set_draw_color(self, color: Color) -> None:
        self.canvas.draw_color = color
        if self.selected is not None:
            self.selected.color = color
            self._redraw()

    def set_thickness(self, thickness: int) -> None:
        self.canvas.thickness = thickness
        if self.selected is not None:
            self.selected.thickness = thickness
            self._redraw()

    def clear_canvas(self) -> None:
        self.shapes.clear()
        self.selected = None
        self.drag_last = None
        self.dirty = False
        self.line_start = None
        self.pending_point = None
        self.canvas.end_stroke()
        self.canvas.clear(self.canvas.background)

    def save_canvas(self) -> None:
        if self.selected is not None:
            self._redraw(highlight=False)  # a moldura azul não vai para o arquivo
        path = datetime.now().strftime("paint_%Y%m%d_%H%M%S.png")
        self.canvas.save_png(path)
        if self.selected is not None:
            self._redraw()
        print(f"Salvo em {path}")

    def quit(self) -> None:
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
            if self.draw_state in (DrawState.FREE, DrawState.ERASER):
                self._bake_shapes()
                self.canvas.begin_stroke(point)
            elif self.draw_state in SHAPE_STATES:
                if not self.shapes:
                    self.base[:] = self.canvas.buffer
                self.selected = None
                self.line_start = point
                self.pending_point = None
            elif self.draw_state == DrawState.FILL:
                self._bake_shapes()
                self.canvas.flood_fill(point)
            elif self.draw_state == DrawState.SELECTING:
                self.selected = self._pick(point)
                self.drag_last = point if self.selected is not None else None
                self.dirty = bool(self.shapes)
        elif action == glfw.RELEASE and self.mouse_pressed:
            point = Point(int(x) - self.sidebar_width, int(y))
            self.mouse_pressed = False
            if self.draw_state in (DrawState.FREE, DrawState.ERASER):
                self.canvas.end_stroke()
            elif self.draw_state in SHAPE_STATES and self.line_start is not None:
                target_point = self._get_effective_endpoint(self.line_start, point)
                if target_point != self.line_start:
                    self.shapes.append(self._make_shape(self.line_start, target_point))
                self.line_start = None
                self.pending_point = None
                self._redraw()
            elif self.draw_state == DrawState.SELECTING:
                self.drag_last = None

    def _on_cursor_pos(self, window, xpos: float, ypos: float) -> None:
        if not self.mouse_pressed:
            return

        point = Point(int(xpos) - self.sidebar_width, int(ypos))
        if self.draw_state in (DrawState.FREE, DrawState.ERASER):
            self.canvas.extend_stroke(point)
        elif self.draw_state in SHAPE_STATES and self.line_start is not None:
            self.pending_point = point
        elif self.draw_state == DrawState.SELECTING and self.drag_last is not None:
            self.selected.translate(point.x - self.drag_last.x, point.y - self.drag_last.y)
            self.drag_last = point
            self.dirty = True

    # ------------------------------------------------------------------
    # Formas: criação, seleção e transformações
    # ------------------------------------------------------------------
    def _make_shape(self, start: Point, end: Point) -> Shape:
        color, thickness = self.canvas.draw_color, self.canvas.thickness
        filled = self.draw_state in FILLED_STATES
        if self.draw_state == DrawState.LINE:
            return Line([start, end], color, thickness)
        if self.draw_state in (DrawState.CIRCLE, DrawState.FILLED_CIRCLE):
            return Circle([start, end], color, thickness, filled)
        if self.draw_state in (DrawState.TRIANGLE, DrawState.FILLED_TRIANGLE):
            apex = Point((start.x + end.x) // 2, start.y)
            return Polygon([apex, end, Point(start.x, end.y)], color, thickness, filled)
        corners = [start, Point(end.x, start.y), end, Point(start.x, end.y)]
        return Polygon(corners, color, thickness, filled)

    def _pick(self, point: Point) -> Shape | None:
        for shape in reversed(self.shapes):
            if shape.contains(point):
                return shape
        return None

    def _transform_selected(self, key: int) -> None:
        if self.selected is None:
            return
        if key == glfw.KEY_LEFT:
            self.selected.rotate(-ROTATE_STEP)
        elif key == glfw.KEY_RIGHT:
            self.selected.rotate(ROTATE_STEP)
        elif key == glfw.KEY_UP:
            self.selected.scale(SCALE_STEP)
        elif key == glfw.KEY_DOWN:
            self.selected.scale(1 / SCALE_STEP)
        else:
            self.shapes.remove(self.selected)
            self.selected = None
        self._redraw()

    def _bake_shapes(self) -> None:
        """Grava as formas no raster (o buffer já as contém) antes de um desenho pixel a pixel."""
        if self.shapes:
            self.selected = None
            self._redraw()
            self.shapes.clear()

    def _redraw(self, highlight: bool = True) -> None:
        """Buffer = camada raster (`base`) + formas + moldura da seleção."""
        self.canvas.buffer[:] = self.base
        for shape in self.shapes:
            shape.draw(self.canvas)
        if highlight and self.selected is not None:
            x0, y0, x1, y1 = self.selected.bounds()
            color, thickness = self.canvas.draw_color, self.canvas.thickness
            self.canvas.draw_color, self.canvas.thickness = SELECTION_COLOR, 1
            self.canvas.draw_polygon([Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)])
            self.canvas.draw_color, self.canvas.thickness = color, thickness

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
        if self.dirty:
            self._redraw()
            self.dirty = False
        if self.pending_point is not None and self.line_start is not None:
            self._redraw()
            target_point = self._get_effective_endpoint(self.line_start, self.pending_point)
            self._make_shape(self.line_start, target_point).draw(self.canvas)
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

