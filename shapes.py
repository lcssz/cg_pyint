"""Formas geométricas (equivalente a src/shapes.zig)."""

from dataclasses import dataclass

from canvas import Point


@dataclass
class Line:
    p0: Point
    pf: Point


@dataclass
class Rectangle:
    y0: Point
    xf: Point


@dataclass
class Triangle:
    p1: Point
    p2: Point
    p3: Point


@dataclass
class Circle:
    center: Point
    radius: int
