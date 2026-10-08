"""Core: janela, loop principal e tratamento de eventos.

Equivalente a src/core.zig.
"""

from __future__ import annotations

import math
from enum import Enum, auto

import pygame

from canvas import Canvas, Point

FPS = 60


class DrawState(Enum):
    FREE = auto()
    LINE = auto()
    SQUARE = auto()
    CIRCLE = auto()
    TRIANGLE = auto()
    FILL = auto()
    CLIPPING = auto()
    SELECTING = auto()


# Tecla -> modo de desenho
KEY_TO_STATE = {
    pygame.K_g: DrawState.FILL,
    pygame.K_1: DrawState.FREE,
    pygame.K_2: DrawState.LINE,
    pygame.K_3: DrawState.CIRCLE,
    pygame.K_4: DrawState.SQUARE,
}


class Core:
    def __init__(self, screen_width: int, screen_height: int) -> None:
        # Só o subsistema de vídeo, como o INIT_FLAGS{ .video = true } original.
        pygame.display.init()
        self.window = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("ImCooked")

        self.canvas = Canvas(self.window)
        self.canvas.clear((255, 255, 255, 255))

        self.running = False
        self.draw_state = DrawState.FREE
        self.line_start: Point | None = None

    def deinit(self) -> None:
        pygame.quit()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                if event.key in KEY_TO_STATE:
                    self.set_draw_state(KEY_TO_STATE[event.key])
            else:
                self.handle_mouse(event)

    def set_draw_state(self, state: DrawState) -> None:
        self.draw_state = state
        # Ao trocar de modo, descarta qualquer coisa pela metade.
        self.line_start = None
        self.canvas.end_stroke()

    def handle_mouse(self, event: pygame.event.Event) -> None:
        handlers = {
            DrawState.FREE: self.handle_free_mode,
            DrawState.LINE: self.handle_line_mode,
            DrawState.CIRCLE: self.handle_circle_mode,
            DrawState.SQUARE: self.handle_square_mode,
            DrawState.FILL: self.handle_fill_mode,
        }
        handler = handlers.get(self.draw_state)
        if handler is not None:
            handler(event)

    def handle_free_mode(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.canvas.begin_stroke(Point(*event.pos))
        elif event.type == pygame.MOUSEMOTION:
            self.canvas.extend_stroke(Point(*event.pos))
        elif event.type == pygame.MOUSEBUTTONUP:
            self.canvas.end_stroke()

    def _two_click(self, event: pygame.event.Event, on_second_click) -> None:
        """Padrão comum de reta/círculo/quadrado: 1º clique guarda o ponto
        inicial, 2º clique desenha e volta ao estado inicial."""
        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        point = Point(*event.pos)
        if self.line_start is not None:
            on_second_click(self.line_start, point)
            self.line_start = None
        else:
            self.line_start = point

    def handle_line_mode(self, event: pygame.event.Event) -> None:
        self._two_click(event, self.canvas.draw_line)

    def handle_circle_mode(self, event: pygame.event.Event) -> None:
        self._two_click(
            event,
            lambda start, point: self.canvas.draw_circle(start, calculate_radius(start, point)),
        )

    def handle_square_mode(self, event: pygame.event.Event) -> None:
        self._two_click(event, self.canvas.draw_square)

    def handle_fill_mode(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.canvas.flood_fill(Point(*event.pos))

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def run(self) -> None:
        self.running = True
        clock = pygame.time.Clock()

        while self.running:
            clock.tick(FPS)
            self.handle_events()
            pygame.display.flip()


def calculate_radius(start: Point, point: Point) -> int:
    dx = point.x - start.x
    dy = point.y - start.y
    return int(math.sqrt(dx * dx + dy * dy))
