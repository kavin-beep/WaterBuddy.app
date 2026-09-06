"""Multi-monitor-safe mascot positioning helpers."""

from __future__ import annotations


def clamp_position(x: int, y: int, width: int, height: int, work_area: tuple[int, int, int, int]) -> tuple[int, int]:
    left, top, right, bottom = work_area
    return max(left, min(x, right - width)), max(top, min(y, bottom - height))


def bottom_right(width: int, height: int, work_area: tuple[int, int, int, int], margin: int = 24) -> tuple[int, int]:
    left, top, right, bottom = work_area
    return clamp_position(right - width - margin, bottom - height - margin, width, height, work_area)

