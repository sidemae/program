"""Render the valve's own metal body and rotating lever into a diagram image.

Only Pillow and the standard library are required.  The image detector deliberately
recognises saturated, slim red/green levers; it does not identify valve function or
infer the operation of real equipment.
"""
from __future__ import annotations

from collections import deque
import math

from PIL import Image, ImageDraw, ImageFilter


def _geometry(background, row):
    width, height = background.size
    unit = width / 1600.0
    cx, cy = row["x"] * width, row["y"] * height
    visual = row.get("visual") or {}
    offset = visual.get("pivot_offset")
    if offset is None:
        offset = (0, -0.027) if row["axis"] == "horizontal" else (-0.016, 0)
    px, py = cx + offset[0] * width, cy + offset[1] * height
    length = max(4.0, visual.get("length", 0.036) * width)
    thickness = max(2.0, visual.get("thickness", 0.006) * width)
    side = visual.get("side", 1)
    horizontal = (row["axis"] == "horizontal") == bool(row["opened"])
    ex, ey = (px + side * length, py) if horizontal else (px, py - length)
    body_half = (27 * unit, 17 * unit) if row["axis"] == "horizontal" else (17 * unit, 27 * unit)
    return cx, cy, px, py, ex, ey, thickness, body_half, visual.get("body", True)


def _rectangle(point_a, point_b, radius):
    return (min(point_a[0], point_b[0]) - radius,
            min(point_a[1], point_b[1]) - radius,
            max(point_a[0], point_b[0]) + radius,
            max(point_a[1], point_b[1]) + radius)


def visual_bounds(background, row):
    """Pixel rectangle enclosing the metal body, spindle and current lever."""
    cx, cy, px, py, ex, ey, thickness, (bx, by), _ = _geometry(background, row)
    handle = _rectangle((px, py), (ex, ey), thickness / 2 + 2)
    return (min(cx - bx, handle[0]), min(cy - by, handle[1]),
            max(cx + bx, handle[2]), max(cy + by, handle[3]))


def _near_segment(x, y, ax, ay, bx, by, tolerance):
    length_sq = (bx - ax) ** 2 + (by - ay) ** 2
    t = max(0., min(1., ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / length_sq)) if length_sq else 0.
    return (x - ax - t * (bx - ax)) ** 2 + (y - ay - t * (by - ay)) ** 2 <= tolerance ** 2


def valve_hit(background, row, x, y):
    """Hit only the body, spindle or lever, including a small click tolerance."""
    cx, cy, px, py, ex, ey, thickness, (bx, by), _ = _geometry(background, row)
    tolerance = max(3., background.width * .002)
    body = abs(x - cx) <= bx + tolerance and abs(y - cy) <= by + tolerance
    spindle = _near_segment(x, y, cx, cy, px, py, max(3., thickness * .4) + tolerance)
    handle = _near_segment(x, y, px, py, ex, ey, thickness / 2 + tolerance)
    return body or spindle or handle


def _metal_body(draw, cx, cy, axis, unit):
    """Small chrome cylinder with flange bands and a central seam."""
    horizontal = axis == "horizontal"
    length, radius = 52 * unit, 15 * unit
    half = length / 2
    bbox = ((cx - half, cy - radius, cx + half, cy + radius) if horizontal
            else (cx - radius, cy - half, cx + radius, cy + half))
    draw.rounded_rectangle(bbox, radius=4 * unit, fill="#677174", outline="#394548", width=max(1, round(1.5 * unit)))
    inner_half = max(1, math.ceil(radius - 2 * unit))
    for offset in range(-inner_half, inner_half + 1):
        t = (offset + inner_half) / max(1, inner_half * 2)
        # The top third is bright while the lower edge remains dark.
        value = int(94 + 149 * math.exp(-((t - .32) / .28) ** 2))
        color = (value, min(255, value + 3), min(255, value + 5))
        if horizontal:
            draw.line((cx - half + 3 * unit, cy + offset, cx + half - 3 * unit, cy + offset), fill=color)
        else:
            draw.line((cx + offset, cy - half + 3 * unit, cx + offset, cy + half - 3 * unit), fill=color)
    for along in (-21, -15, 15, 21):
        position = along * unit
        if horizontal:
            draw.line((cx + position, cy - radius, cx + position, cy + radius), fill="#434b4e", width=max(1, round(2 * unit)))
            draw.line((cx + position + 2 * unit, cy - radius + unit, cx + position + 2 * unit, cy + radius - unit), fill="#e8eaeb", width=max(1, round(unit)))
        else:
            draw.line((cx - radius, cy + position, cx + radius, cy + position), fill="#434b4e", width=max(1, round(2 * unit)))
            draw.line((cx - radius + unit, cy + position + 2 * unit, cx + radius - unit, cy + position + 2 * unit), fill="#e8eaeb", width=max(1, round(unit)))
    seam = (cx, cy - radius, cx, cy + radius) if horizontal else (cx - radius, cy, cx + radius, cy)
    draw.line(seam, fill="#788184", width=max(1, round(unit)))


def _lever(draw, px, py, ex, ey, thickness, opened):
    horizontal = abs(ex - px) > abs(ey - py)
    radius = thickness / 2
    bbox = _rectangle((px, py), (ex, ey), radius)
    dark = "#065b17" if opened else "#850b0a"
    middle = "#04a51e" if opened else "#ee1914"
    bright = "#60e66e" if opened else "#ff7771"
    draw.rounded_rectangle(bbox, radius=radius, fill=dark)
    inner = (bbox[0] + 1, bbox[1] + 1, bbox[2] - 1, bbox[3] - 1)
    if inner[2] > inner[0] and inner[3] > inner[1]:
        draw.rounded_rectangle(inner, radius=min(max(0, radius - 1), (inner[2] - inner[0]) / 2, (inner[3] - inner[1]) / 2), fill=middle)
    offset = max(1, thickness * .23)
    inset = max(2, thickness * .45)
    if horizontal and abs(ex - px) >= inset * 2:
        draw.line((min(px, ex) + inset, py - offset, max(px, ex) - inset, py - offset), fill=bright, width=max(1, round(thickness * .13)))
    elif not horizontal and abs(ey - py) >= inset * 2:
        draw.line((px - offset, min(py, ey) + inset, px - offset, max(py, ey) - inset), fill=bright, width=max(1, round(thickness * .13)))
    # A small metal hinge belongs to the handle; it is not a status button.
    hinge = max(2., thickness * .42)
    draw.ellipse((px - hinge, py - hinge, px + hinge, py + hinge), fill="#b4c1bf", outline="#334a4a", width=max(1, round(thickness * .1)))
    bolt = max(1., hinge * .42)
    draw.ellipse((px - bolt, py - bolt, px + bolt, py + bolt), fill="#586a6a")


def render_scene(background, rows):
    """Return the complete RGB picture with each valve in its current pose."""
    image = background.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    unit = image.width / 1600.
    for row in rows:
        cx, cy, px, py, ex, ey, thickness, _, body = _geometry(image, row)
        if body:
            _metal_body(draw, cx, cy, row["axis"], unit)
            stem_width = max(2, round(thickness * .5))
            draw.line((cx, cy, px, py), fill="#465355", width=stem_width + 2)
            draw.line((cx, cy, px, py), fill="#ccd3d4", width=stem_width)
        _lever(draw, px, py, ex, ey, thickness, row["opened"])
    return image


def _color(pixel):
    r, g, b = pixel
    if r >= 105 and r >= g * 1.65 and r >= b * 1.55 and r - max(g, b) >= 55:
        return 1
    if g >= 75 and g >= r * 1.75 and g >= b * 1.7 and g - max(r, b) >= 35:
        return 2
    return 0


def _metal(pixel):
    maximum, minimum = max(pixel), min(pixel)
    return maximum - minimum <= 28 and 35 <= maximum <= 210


def _metal_score(pixels, size, point, mask):
    width, height = size
    x, y = point
    score = 0
    for sy in range(max(0, round(y) - 11), min(height, round(y) + 12)):
        for sx in range(max(0, round(x) - 11), min(width, round(x) + 12)):
            if (sx - x) ** 2 + (sy - y) ** 2 <= 121 and not mask[sy * width + sx] and _metal(pixels[sx, sy]):
                score += 1
    return score


def _light_surrounding(pixels, size, box):
    """A diagram lever sits mostly on paper, unlike a compressor housing."""
    width, height = size
    x0, y0, x1, y1 = box
    light = total = 0
    for y in range(max(0, y0 - 7), min(height, y1 + 8)):
        for x in range(max(0, x0 - 7), min(width, x1 + 8)):
            if x0 - 2 <= x <= x1 + 2 and y0 - 2 <= y <= y1 + 2:
                continue
            total += 1
            pixel = pixels[x, y]
            if min(pixel) >= 220 and max(pixel) - min(pixel) <= 35:
                light += 1
    return light / max(1, total)


def _body_center(pixels, size, pivot, axis):
    """Look for compact metal near the expected spindle attachment."""
    width, height = size
    px, py = pivot
    if axis == "horizontal":
        candidates = [(px + dx, py + dy) for dx in range(-20, 21, 5) for dy in range(18, 40, 5)]
        fallback = (px, py + 26)
        half = (18, 9)
    else:
        candidates = [(px + dx, py + dy) for dx in (-38, -33, -28, -23, -18, 18, 23, 28, 33, 38) for dy in range(-15, 16, 5)]
        fallback = (px + 26, py)
        half = (9, 18)
    best, best_score = fallback, 0
    for x, y in candidates:
        score = 0
        for sy in range(max(0, round(y - half[1])), min(height, round(y + half[1]) + 1), 2):
            for sx in range(max(0, round(x - half[0])), min(width, round(x + half[0]) + 1), 2):
                if _metal(pixels[sx, sy]):
                    score += 1
        # Prefer the expected attachment when several candidates sit on a pipe.
        score -= math.hypot(x - fallback[0], y - fallback[1]) * .16
        if score > best_score:
            best, best_score = (x, y), score
    return best


def _remove_handles(image, components):
    """Replace only handle silhouettes, keeping neighbouring metal intact."""
    width, height = image.size
    original = image.load()
    clean = image.copy()
    output = clean.load()
    for component in components:
        points, color, pivot, end = component
        horizontal = abs(end[0] - pivot[0]) > abs(end[1] - pivot[1])
        axis = "horizontal" if horizontal == (color == 2) else "vertical"
        body_x, body_y = _body_center(original, image.size, pivot, axis)
        body_half = (24, 14) if axis == "horizontal" else (14, 24)
        mask = Image.new("L", image.size)
        mp = mask.load()
        for index in points:
            mp[index % width, index // width] = 255
        # Three pixels reach antialiasing and the dark lever edge.  This is a
        # silhouette dilation, never a rectangle over the neighbouring body.
        mask = mask.filter(ImageFilter.MaxFilter(7))
        box = mask.getbbox()
        if box is None:
            continue
        mp = mask.load()
        for y in range(box[1], box[3]):
            for x in range(box[0], box[2]):
                if not mp[x, y]:
                    continue
                if _metal(original[x, y]) and math.hypot(x - pivot[0], y - pivot[1]) < 6:
                    continue
                if _metal(original[x, y]):
                    # Keep metal that continues perpendicular to the handle.
                    # Its body/spindle is wider than a one-pixel lever outline.
                    normal = ((0, 1), (0, -1)) if horizontal else ((1, 0), (-1, 0))
                    structural = False
                    for nx, ny in normal:
                        neighbours = [(x + nx * distance, y + ny * distance) for distance in range(1, 5)]
                        if sum(0 <= sx < width and 0 <= sy < height and _metal(original[sx, sy])
                               for sx, sy in neighbours) >= 3:
                            structural = True
                            break
                    if structural:
                        continue
                # Nearby unmasked light neutral pixels normally are the diagram's
                # white background. Sampling them also supports tinted paper.
                samples = []
                metal_samples = []
                for distance in (4, 7, 11, 15):
                    normal_points = ((x, y - distance), (x, y + distance)) if horizontal else ((x - distance, y), (x + distance, y))
                    pair = [original[sx, sy] for sx, sy in normal_points
                            if 0 <= sx < width and 0 <= sy < height and not mp[sx, sy] and _metal(original[sx, sy])]
                    if len(pair) == 2:
                        # Restore a thin handle crossing a metal body from the
                        # body's neighbouring shades instead of painting white.
                        samples = pair
                        break
                if samples:
                    output[x, y] = tuple(round(sum(p[k] for p in samples) / len(samples)) for k in range(3))
                    continue
                for distance in (4, 7, 11):
                    for dx, dy in ((distance, 0), (-distance, 0), (0, distance), (0, -distance),
                                   (distance, distance), (-distance, -distance)):
                        sx, sy = x + dx, y + dy
                        if 0 <= sx < width and 0 <= sy < height and not mp[sx, sy]:
                            sample = original[sx, sy]
                            if max(sample) - min(sample) <= 35 and min(sample) >= 220:
                                samples.append(sample)
                            elif _metal(sample) and (dy != 0 if horizontal else dx != 0):
                                metal_samples.append(sample)
                    in_body = abs(x - body_x) <= body_half[0] and abs(y - body_y) <= body_half[1]
                    if in_body and metal_samples:
                        samples = metal_samples
                        break
                    if samples:
                        break
                if not samples and metal_samples:
                    samples = metal_samples
                if samples:
                    output[x, y] = tuple(round(sum(p[k] for p in samples) / len(samples)) for k in range(3))
                else:
                    # Do not erase machinery when its background cannot be
                    # inferred locally. Conservatively keep the source pixel.
                    output[x, y] = original[x, y]
    return clean


def prepare_image(image):
    """Find narrow coloured levers and return a cleaned RGB image and rows.

    Coordinates and handle measurements are normalized to the source dimensions.
    Large actuators, round wheels and muted compressor bodies are filtered out.
    Images without recognised levers are returned without pixel changes.
    """
    image = image.convert("RGB")
    width, height = image.size
    # Preserve the common reference raster exactly; cap much larger diagrams.
    factor = min(1., 2400. / width)
    work = image.resize((max(1, round(width * factor)), max(1, round(height * factor))), Image.Resampling.LANCZOS) if factor != 1 else image
    ww, wh = work.size
    reference_scale = ww / 1600.
    pixels = work.load()
    colors = bytearray(_color(pixel) for pixel in work.getdata())
    visited = bytearray(ww * wh)
    components = []
    for index, color in enumerate(colors):
        if not color or visited[index]:
            continue
        queue = deque([index])
        visited[index] = 1
        points = []
        while queue:
            current = queue.popleft()
            points.append(current)
            x, y = current % ww, current // ww
            for ny in range(max(0, y - 1), min(wh, y + 2)):
                for nx in range(max(0, x - 1), min(ww, x + 2)):
                    neighbour = ny * ww + nx
                    if not visited[neighbour] and colors[neighbour] == color:
                        visited[neighbour] = 1
                        queue.append(neighbour)
        xs = [p % ww for p in points]
        ys = [p // ww for p in points]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        long, short = max(bw, bh), min(bw, bh)
        if not (20 * reference_scale <= long <= 90 * reference_scale and
                max(2, 3 * reference_scale) <= short <= 17 * reference_scale and
                long / short >= 2.5 and .38 <= len(points) / (bw * bh) <= 1):
            continue
        if color == 2 and _light_surrounding(pixels, work.size, (x0, y0, x1, y1)) < .45:
            continue
        horizontal = bw >= bh
        ends = ((x0 + short / 2, (y0 + y1) / 2), (x1 - short / 2, (y0 + y1) / 2)) if horizontal else (((x0 + x1) / 2, y0 + short / 2), ((x0 + x1) / 2, y1 - short / 2))
        scores = [_metal_score(pixels, work.size, p, colors) for p in ends]
        if max(scores) < 5:
            # A lever is connected to a small metal hinge or valve spindle.
            continue
        proximal = (0 if horizontal else 1) if abs(scores[0] - scores[1]) < 3 else int(scores[1] > scores[0])
        pivot, end = ends[proximal], ends[1 - proximal]
        components.append((points, color, pivot, end))
    if not components:
        return image.copy(), []
    clean_work = _remove_handles(work, components)
    rows = []
    for points, color, pivot, end in sorted(components, key=lambda item: (item[2][1], item[2][0])):
        opened = color == 2
        handle_horizontal = abs(end[0] - pivot[0]) > abs(end[1] - pivot[1])
        axis = "horizontal" if handle_horizontal == opened else "vertical"
        cx, cy = _body_center(pixels, work.size, pivot, axis)
        # Stay within the image even when the original handle touches its edge.
        cx, cy = min(ww - 1, max(0, cx)), min(wh - 1, max(0, cy))
        long = max(max(p % ww for p in points) - min(p % ww for p in points) + 1,
                   max(p // ww for p in points) - min(p // ww for p in points) + 1)
        short = min(max(p % ww for p in points) - min(p % ww for p in points) + 1,
                    max(p // ww for p in points) - min(p // ww for p in points) + 1)
        rows.append({"id": f"V{len(rows) + 1:02}", "name": f"밸브 {len(rows) + 1}",
                     "x": cx / ww, "y": cy / wh, "axis": axis, "opened": opened,
                     "visual": {"pivot_offset": [(pivot[0] - cx) / ww, (pivot[1] - cy) / wh],
                                "length": max(4, long - short) / ww,
                                "thickness": short / ww,
                                "side": 1 if not handle_horizontal or end[0] >= pivot[0] else -1,
                                "body": False}})
    if factor == 1:
        return clean_work, rows
    # Apply the local cleaning mask to the full-resolution original, preserving
    # all source pixels outside those small lever regions.
    changed = Image.new("L", work.size)
    changed.putdata([255 if a != b else 0 for a, b in zip(work.getdata(), clean_work.getdata())])
    changed = changed.resize(image.size, Image.Resampling.NEAREST)
    replacement = clean_work.resize(image.size, Image.Resampling.BICUBIC)
    return Image.composite(replacement, image, changed), rows
