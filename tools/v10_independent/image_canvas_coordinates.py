from __future__ import annotations

from typing import Any


def image_item_to_source(
    canvas: Any,
    image_item: int | str | None,
    source_size: tuple[int, int],
    event_x: float,
    event_y: float,
    *,
    render_generation: int = 0,
) -> tuple[tuple[float, float] | None, dict[str, Any]]:
    """Map one Tk canvas event to source pixels through the rendered image item.

    Both the pointer and item bounds remain in Tk canvas coordinates.  No screen,
    native-client, monitor-DPI, or surrounding-widget dimensions participate in
    the image transform.
    """
    if image_item is None:
        raise ValueError("No rendered canvas image item is available.")
    bbox = canvas.bbox(image_item)
    if bbox is None or len(bbox) != 4:
        raise ValueError("The rendered canvas image item has no usable bounds.")
    left, top, right, bottom = (float(value) for value in bbox)
    displayed_width = right - left
    displayed_height = bottom - top
    source_width, source_height = source_size
    if displayed_width <= 0 or displayed_height <= 0:
        raise ValueError("The rendered canvas image item has empty bounds.")
    if source_width <= 0 or source_height <= 0:
        raise ValueError("Source image dimensions must be positive.")

    canvas_x = float(canvas.canvasx(event_x))
    canvas_y = float(canvas.canvasy(event_y))
    x_fraction = (canvas_x - left) / displayed_width
    y_fraction = (canvas_y - top) / displayed_height
    provenance = {
        "coordinate_system": "tk_canvas_image_item_to_source_pixels",
        "source_dimensions": [source_width, source_height],
        "rendered_image_bbox": [left, top, right, bottom],
        "rendered_image_dimensions": [displayed_width, displayed_height],
        "canvas_event": [float(event_x), float(event_y)],
        "canvas_point": [canvas_x, canvas_y],
        "image_fraction": [x_fraction, y_fraction],
        "render_generation": int(render_generation),
    }
    if not (0.0 <= x_fraction < 1.0 and 0.0 <= y_fraction < 1.0):
        return None, provenance
    source_point = (x_fraction * source_width, y_fraction * source_height)
    provenance["source_point"] = list(source_point)
    return source_point, provenance


def source_to_image_item(
    canvas: Any,
    image_item: int | str | None,
    source_size: tuple[int, int],
    source_x: float,
    source_y: float,
) -> tuple[float, float]:
    """Map source pixels back to the currently rendered Tk image item."""
    if image_item is None:
        raise ValueError("No rendered canvas image item is available.")
    bbox = canvas.bbox(image_item)
    if bbox is None or len(bbox) != 4:
        raise ValueError("The rendered canvas image item has no usable bounds.")
    left, top, right, bottom = (float(value) for value in bbox)
    source_width, source_height = source_size
    if source_width <= 0 or source_height <= 0:
        raise ValueError("Source image dimensions must be positive.")
    return (
        left + float(source_x) / source_width * (right - left),
        top + float(source_y) / source_height * (bottom - top),
    )

