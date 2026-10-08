"""Rebuild the reviewed GC-1512A project from its unmodified source raster.

The pixel registrations are independently reviewed in assets/registration.json.
Runtime installation does not require this development helper or PDF tooling.
"""
from copy import deepcopy
import base64
import io
import json
import math
from pathlib import Path
import zipfile

from PIL import Image

import valve_control as program
import valve_render

HERE = Path(__file__).resolve().parent


def build_reference():
    assets = HERE / "assets"
    with Image.open(assets / "GC-1512A.png") as image:
        source = image.convert("RGB")
    registry = json.loads((assets / "registration.json").read_text(encoding="utf-8"))
    assert list(source.size) == registry["image_size"]
    clean, detected = valve_render.prepare_image(source)
    assert len(detected) == 21
    used, result = set(), []

    def select(bounds):
        target = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
        distances = []
        for index, row in enumerate(detected):
            if index in used:
                continue
            artwork = row["visual"]["artwork"]
            px = (row["x"] + row["visual"]["pivot_offset"][0]) * source.width
            py = (row["y"] + row["visual"]["pivot_offset"][1]) * source.height
            center = (px + (artwork["offset"][0] + artwork["size"][0] / 2) * source.width,
                      py + (artwork["offset"][1] + artwork["size"][1] / 2) * source.height)
            distances.append((math.dist(target, center), index))
        distance, index = min(distances)
        assert distance < 12, (bounds, distance)
        used.add(index)
        return deepcopy(detected[index])

    def register(row, entry):
        artwork = row["visual"]["artwork"]
        old_pivot = ((row["x"] + row["visual"]["pivot_offset"][0]) * source.width,
                     (row["y"] + row["visual"]["pivot_offset"][1]) * source.height)
        old_left = old_pivot[0] + artwork["offset"][0] * source.width
        old_top = old_pivot[1] + artwork["offset"][1] * source.height
        cx, cy = entry["body"]
        px, py = entry["pivot"]
        assert row["opened"] == entry["initial_opened"]
        row.update(id=entry["id"], name=entry["name"], x=cx / source.width,
                   y=cy / source.height, axis=entry["axis"])
        row["visual"]["pivot_offset"] = [(px - cx) / source.width, (py - cy) / source.height]
        row["visual"]["side"] = (-1 if px < cx else 1) if entry["axis"] == "vertical" else (
            -1 if (entry["lever_bounds"][0] + entry["lever_bounds"][2]) / 2 < px else 1)
        row["visual"]["turn"] = entry["turn"]
        artwork["offset"] = [(old_left - px) / source.width, (old_top - py) / source.height]
        return valve_render.register_artwork(clean, source, row)

    def fixed_control(entry):
        left, top, right, bottom = entry["actuator_bounds"]
        sprite = source.crop((left, top, right, bottom)).convert("RGBA")
        mask = Image.new("L", sprite.size)
        source_channel = 1 if entry["id"] in ("CV01", "AV02") else 0 if entry["id"] == "HV06" else 2
        for y in range(sprite.height):
            for x in range(sprite.width):
                r, g, b, _ = sprite.getpixel((x, y))
                # Preserve chrome, paper, brass fittings and adjacent levers.
                if entry["id"] == "CV01" and left + x <= 689 and top + y >= 212:
                    continue
                channels = (r, g, b)
                pigment = channels[source_channel]
                opposite = max(value for index, value in enumerate(channels) if index != source_channel)
                if pigment - opposite >= 5 and pigment - min(channels) >= 12:
                    mask.putpixel((x, y), 255)
        assert mask.getbbox() is not None, entry["id"]
        sprite.putalpha(mask)
        cx, cy = entry["body"]
        px, py = entry["pivot"]
        visual = {"pivot_offset": [(px - cx) / source.width, (py - cy) / source.height],
                  "length": max(sprite.size) / source.width,
                  "thickness": min(8, min(sprite.size)) / source.width,
                  "side": 1, "body": False, "kind": entry["kind"],
                  "artwork": valve_render._encode_artwork(sprite, source.size, left, top,
                                                           (px, py), entry["initial_opened"], entry["axis"])}
        return dict(id=entry["id"], name=entry["name"], x=cx / source.width,
                    y=cy / source.height, axis=entry["axis"], opened=entry["initial_opened"], visual=visual)

    def repair_drain_legs(row, entry):
        # The pictured red drain grip occludes two vertical support columns.
        # Their hidden texture cannot be copied from white paper. Interpolate
        # each reviewed source column between unobstructed rows instead.
        repair = (544, 858, 591, 889)
        for x in range(repair[0], repair[2]):
            above = source.getpixel((x, 853))
            below = source.getpixel((x, 889))
            for y in range(repair[1], repair[3]):
                fraction = (y - 853) / 36
                clean.putpixel((x, y), tuple(round(a * (1 - fraction) + b * fraction)
                                              for a, b in zip(above, below)))
        artwork = row["visual"]["artwork"]
        px, py = entry["pivot"]
        left = round(px + artwork["offset"][0] * source.width)
        top = round(py + artwork["offset"][1] * source.height)
        original = valve_render._decode_artwork(artwork["png"])
        moving = valve_render._decode_artwork(artwork.get("moving_png", artwork["png"]))
        extent = (min(left, repair[0]), min(top, repair[1]),
                  max(left + original.width, repair[2]), max(top + original.height, repair[3]))
        alpha = Image.new("L", (extent[2] - extent[0], extent[3] - extent[1]))
        alpha.paste(original.getchannel("A"), (left - extent[0], top - extent[1]))
        for y in range(repair[1], repair[3]):
            for x in range(repair[0], repair[2]):
                if clean.getpixel((x, y)) != source.getpixel((x, y)):
                    alpha.putpixel((x - extent[0], y - extent[1]), 255)
        restored = source.crop(extent).convert("RGBA")
        restored.putalpha(alpha)
        foreground = Image.new("RGBA", restored.size)
        foreground.paste(moving, (left - extent[0], top - extent[1]))
        row["visual"]["artwork"] = valve_render._encode_artwork(
            restored, source.size, extent[0], extent[1], (px, py), row["opened"], row["axis"])
        buffer = io.BytesIO()
        foreground.save(buffer, format="PNG")
        row["visual"]["artwork"]["moving_png"] = base64.b64encode(buffer.getvalue()).decode("ascii")

    for entry in registry["valves"]:
        if entry.get("kind") in ("actuator", "wheel"):
            result.append(fixed_control(entry))
            continue
        row = register(select(entry["lever_bounds"]), entry)
        if entry["id"] == "V17":
            repair_drain_legs(row, entry)
        if entry["id"] == "V18":
            # AV02's painted shell ends immediately beside this grip. Its edge
            # belongs to the stationary automatic valve, never the rotating
            # manual lever. Keep it only in initial reconstruction artwork.
            artwork = row["visual"]["artwork"]
            px, _ = entry["pivot"]
            left = round(px + artwork["offset"][0] * source.width)
            moving = valve_render._decode_artwork(artwork["moving_png"]).copy()
            for x in range(min(moving.width, max(0, entry["lever_bounds"][0] - left))):
                for y in range(moving.height):
                    r, g, b, _ = moving.getpixel((x, y))
                    moving.putpixel((x, y), (r, g, b, 0))
            buffer = io.BytesIO()
            moving.save(buffer, format="PNG")
            artwork["moving_png"] = base64.b64encode(buffer.getvalue()).decode("ascii")
        # Registering the omitted grip cleans its entire original silhouette and
        # arm. It is deliberately not added to the project or moving artwork.
        for bounds in entry.get("removed_lever_bounds", []):
            register(select(bounds), entry)
            # The old L-shaped drawing places the second grip tip inside the
            # first grip's JPEG halo. Remove that overlap from BOTH retained
            # sprites, as well as its bent arm on the static background.
            removal = (bounds[0] - 12, bounds[1] - 4,
                       bounds[2] + 12, bounds[3] + 5)
            clean.paste((255, 255, 255), removal)
            artwork = row["visual"]["artwork"]
            px, py = entry["pivot"]
            left = round(px + artwork["offset"][0] * source.width)
            top = round(py + artwork["offset"][1] * source.height)
            for key in ("png", "moving_png"):
                if key not in artwork:
                    continue
                with Image.open(io.BytesIO(base64.b64decode(artwork[key]))) as image:
                    sprite = image.convert("RGBA")
                for y in range(sprite.height):
                    for x in range(sprite.width):
                        if removal[0] <= left + x < removal[2] and removal[1] <= top + y < removal[3]:
                            r, g, b, _ = sprite.getpixel((x, y))
                            sprite.putpixel((x, y), (r, g, b, 0))
                buffer = io.BytesIO()
                sprite.save(buffer, format="PNG")
                artwork[key] = base64.b64encode(buffer.getvalue()).decode("ascii")
        result.append(row)
    assert len(used) == 21 and len(result) == 29
    assert not any(row["id"] == "V21" for row in result)
    document = dict(schema_version=1, coordinate_system=program.COORDINATES,
                    mode="simulation", valves=result)
    program.validate(document)
    for row in result:
        assert valve_render.valve_hit(clean, row, row["x"] * source.width, row["y"] * source.height)
    png = io.BytesIO()
    clean.save(png, format="PNG")
    with zipfile.ZipFile(assets / "GC-1512A.vcp", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("project.json", json.dumps(document, ensure_ascii=False, indent=2))
        archive.writestr("background.png", png.getvalue())
    valve_render.render_scene(clean, result).save(assets / "GC-1512A.initial.png")
    print(f"Built {len(result)} controls: {sum(row['opened'] for row in result)} open, single V08 lever.")


if __name__ == "__main__":
    build_reference()
