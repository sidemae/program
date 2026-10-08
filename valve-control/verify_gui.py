"""Exercise the real Tk application and capture reproducible verification results."""
from __future__ import annotations

import copy
import json
import os
import platform
import select
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import PIL
from PIL import Image, ImageChops, ImageDraw, ImageGrab
from tkinter import messagebox

import valve_control as program

HERE = Path(__file__).resolve().parent


def start_display():
    """Use the current display, or own a temporary isolated Xvfb display."""
    if sys.platform == "win32" or os.environ.get("DISPLAY"):
        return None
    executable = shutil.which("Xvfb") or "/workspace/.cloud-setup/root/usr/bin/Xvfb"
    if not Path(executable).exists():
        raise RuntimeError("디스플레이가 없습니다. Xvfb 설치 후 검증하세요.")
    process = subprocess.Popen(
        [executable, "-displayfd", "1", "-screen", "0", "1600x1050x24", "-nolisten", "tcp"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if not select.select([process.stdout], [], [], 10)[0]:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError("Xvfb 준비 시간 초과")
    display = process.stdout.readline().strip()
    if not display.isdigit():
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError("Xvfb 시작 실패: " + process.stderr.read())
    os.environ["DISPLAY"] = ":" + display
    return process


def main():
    display = start_display()
    app = None
    checks = []
    errors = []
    output = HERE / "artifacts"
    output.mkdir(exist_ok=True)
    try:
        with ExitStack() as stack, tempfile.TemporaryDirectory(prefix="valve-release-check-") as temp:
            stack.enter_context(patch.object(messagebox, "askyesno", return_value=True))
            stack.enter_context(patch.object(messagebox, "askyesnocancel", return_value=False))
            stack.enter_context(patch.object(messagebox, "showerror"))
            stack.enter_context(patch.object(messagebox, "showwarning"))
            stack.enter_context(patch.object(messagebox, "showinfo"))
            app = program.App()
            app.report_callback_exception = lambda *args: errors.append("".join(traceback.format_exception(*args)))
            temp = Path(temp)
            initial_count = len(app.valves)
            initial_open_count = sum(row["opened"] for row in app.valves)
            reference_path = HERE / "assets" / "GC-1512A.png"
            reference_bytes = reference_path.read_bytes() if reference_path.exists() else None

            def check(name, condition):
                if not condition:
                    raise AssertionError(name)
                checks.append(name)
                print("PASS:", name, flush=True)

            def settle():
                app.update()
                app.draw()
                app.update()
                if errors:
                    raise AssertionError("Tk callback error: " + "\n".join(errors))

            def valve(identifier):
                return next(row for row in app.valves if row["id"] == identifier)

            def press(x, y):
                app.canvas.event_generate("<ButtonPress-1>", x=round(x), y=round(y))
                app.canvas.event_generate("<ButtonRelease-1>", x=round(x), y=round(y))
                settle()

            def click(identifier):
                press(*app.screen(valve(identifier)))

            def snapshot():
                return (copy.deepcopy(app.valves), app.background.size, app.background.tobytes(),
                        app.rendered_image.tobytes(), app.selected, app.project_path, app.dirty)

            def capture(filename):
                settle()
                x, y = app.winfo_rootx(), app.winfo_rooty()
                ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).save(output / filename)

            def only_picture():
                return [app.canvas.type(item) for item in app.canvas.find_all()] == ["image"]

            def is_color(pixel, color):
                red, green, blue = pixel[:3]
                return (green > 60 and green > red * 1.25 and green > blue * 1.25
                        if color == "green" else red > 80 and red > green * 1.4 and red > blue * 1.4)

            def lever_region(row):
                width, height = app.background.size
                visual = row.get("visual", {})
                dx, dy = visual.get("pivot_offset", (0, 0))
                x, y = (row["x"] + dx) * width, (row["y"] + dy) * height
                radius = visual.get("length", 0.035) * width + visual.get("thickness", 0.005) * width * 2 + 5
                return (max(0, int(x - radius)), max(0, int(y - radius)),
                        min(width, int(x + radius + 1)), min(height, int(y + radius + 1)))

            def color_geometry(row, color):
                left, top, right, bottom = lever_region(row)
                image = app.rendered_image.crop((left, top, right, bottom))
                remaining = {(x, y) for y in range(image.height) for x in range(image.width)
                             if is_color(image.getpixel((x, y)), color)}
                if not remaining:
                    return None
                components = []
                while remaining:
                    pending = [remaining.pop()]
                    component = []
                    while pending:
                        x, y = pending.pop()
                        component.append((x, y))
                        for near_y in range(y - 1, y + 2):
                            for near_x in range(x - 1, x + 2):
                                neighbor = (near_x, near_y)
                                if neighbor in remaining:
                                    remaining.remove(neighbor)
                                    pending.append(neighbor)
                    components.append(component)
                width, height = app.background.size
                visual = row.get("visual", {})
                dx, dy = visual.get("pivot_offset", (0, 0))
                target_x, target_y = (row["x"] + dx) * width - left, (row["y"] + dy) * height - top
                distance = visual.get("length", 0.036) * width * 0.55
                if (row["axis"] == "horizontal") == row["opened"]:
                    target_x += visual.get("side", 1) * distance
                else:
                    target_y -= distance
                points = min(components, key=lambda component: min((x - target_x) ** 2 + (y - target_y) ** 2
                                                                 for x, y in component))
                if min((x - target_x) ** 2 + (y - target_y) ** 2 for x, y in points) > 100:
                    return None
                return (max(p[0] for p in points) - min(p[0] for p in points) + 1,
                        max(p[1] for p in points) - min(p[1] for p in points) + 1)

            def lever_matches(row):
                geometry = color_geometry(row, "green" if row["opened"] else "red")
                horizontal = (row["axis"] == "horizontal") == row["opened"]
                if not geometry:
                    return False
                span_x, span_y = geometry
                return span_x > 2 * span_y if horizontal else span_y > 2 * span_x

            def lever_tip(row):
                width, height = app.background.size
                visual = row["visual"]
                dx, dy = visual["pivot_offset"]
                x, y = (row["x"] + dx) * width, (row["y"] + dy) * height
                distance = visual["length"] * width * 0.8
                horizontal = (row["axis"] == "horizontal") == row["opened"]
                if horizontal:
                    x += visual["side"] * distance
                else:
                    y -= distance
                return app.screen(dict(x=x / width, y=y / height))

            def expect_rejected(path, loader):
                before = snapshot()
                rejected = False
                try:
                    loader(path)
                except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
                    rejected = True
                settle()
                return rejected and snapshot() == before

            settle()
            check("reference diagram starts with mixed pictured valve states", initial_count >= 20
                  and 0 < initial_open_count < initial_count
                  and f"열림 {initial_open_count}" in app.counts.get()
                  and f"닫힘 {initial_count - initial_open_count}" in app.counts.get())
            with Image.open(reference_path) as reference_image:
                reference_size = reference_image.size
            check("reference source image is loaded without modifying its file", app.background.size == reference_size
                  and app.reference_loaded and reference_path.read_bytes() == reference_bytes)
            check("normal canvas contains only the rendered diagram image", only_picture())
            check("initial pictured lever is green and parallel to its horizontal pipe", lever_matches(valve("V01")))
            capture("implementation_closed.png")
            untouched = app.rendered_image.copy()
            click("V01")
            check("horizontal pictured lever closes red and perpendicular on real click", not valve("V01")["opened"]
                  and lever_matches(valve("V01")) and f"열림 {initial_open_count - 1}" in app.counts.get())
            changed = ImageChops.difference(untouched, app.rendered_image).getbbox()
            left, top, right, bottom = lever_region(valve("V01"))
            check("click redraw changes only the selected pictured valve region", changed is not None
                  and left <= changed[0] <= changed[2] <= right and top <= changed[1] <= changed[3] <= bottom)
            click("V01")
            check("horizontal pictured lever opens green and parallel on second click", valve("V01")["opened"]
                  and lever_matches(valve("V01")) and only_picture())
            press(*lever_tip(valve("V01")))
            check("pictured lever tip is clickable beyond the valve body", not valve("V01")["opened"]
                  and lever_matches(valve("V01")))
            click("V01")
            before = copy.deepcopy(app.valves)
            press(2, 2)
            check("background click does not toggle a valve", app.valves == before)
            click("V09")
            check("neighboring pictured valve keeps its independent open state", not valve("V09")["opened"] and valve("V10")["opened"])
            click("V10")
            check("nearest pictured hit selects adjacent valve independently", not valve("V09")["opened"] and not valve("V10")["opened"])
            app.geometry("1080x760")
            settle()
            check("minimum size keeps properties and operation log visible", app.log.winfo_ismapped()
                  and app.log.winfo_rooty() + app.log.winfo_height() <= app.winfo_rooty() + app.winfo_height())
            click("V06")
            check("minimum-size resize preserves pictured lever click alignment", valve("V06")["opened"]
                  and lever_matches(valve("V06")) and only_picture())
            app.geometry("1440x950")
            settle()
            click("V12")
            click("V20")
            check("vertical pictured lever closes red and perpendicular to vertical pipe", not valve("V20")["opened"]
                  and lever_matches(valve("V20")))
            click("V20")
            check("vertical pictured lever opens green and parallel to vertical pipe", valve("V20")["opened"]
                  and lever_matches(valve("V20")))
            capture("implementation_open.png")

            app.editing.set(True)
            target = valve("V01")
            original_state, old_x, old_y = target["opened"], target["x"], target["y"]
            x, y = app.screen(target)
            app.canvas.event_generate("<ButtonPress-1>", x=round(x), y=round(y))
            app.canvas.event_generate("<B1-Motion>", x=round(x + 35), y=round(y + 25))
            app.canvas.event_generate("<ButtonRelease-1>", x=round(x + 35), y=round(y + 25))
            settle()
            check("editing drag changes position without changing state", target["x"] > old_x
                  and target["y"] > old_y and target["opened"] == original_state)
            x, y = app.screen(target)
            app.canvas.event_generate("<ButtonPress-1>", x=round(x), y=round(y))
            app.canvas.event_generate("<B1-Motion>", x=-100, y=-100)
            app.canvas.event_generate("<ButtonRelease-1>", x=-100, y=-100)
            settle()
            check("editing drag never places valve outside image", 0 <= target["x"] <= 1 and 0 <= target["y"] <= 1)

            app.adding = True
            previous_ids = {row["id"] for row in app.valves}
            anchor = dict(target, x=0.17, y=0.17)
            press(*app.screen(anchor))
            added_ids = {row["id"] for row in app.valves} - previous_ids
            check("real canvas add creates one selected valve", len(added_ids) == 1
                  and len(app.valves) == initial_count + 1 and app.selected in added_ids)
            added_id = next(iter(added_ids))
            app.name_var.set("검증용 새 밸브")
            app.axis_var.set("vertical")
            app.apply_properties()
            settle()
            check("property editor renames valve and changes axis", valve(added_id)["name"] == "검증용 새 밸브"
                  and valve(added_id)["axis"] == "vertical")
            app.toggle(added_id)
            settle()
            check("editing mode protects state from toggle controls", not valve(added_id)["opened"])
            app.editing.set(False)
            app.mode_changed()
            app.tree.see(added_id)
            settle()
            row_x, row_y, row_width, row_height = app.tree.bbox(added_id)
            for _ in range(2):
                app.tree.event_generate("<ButtonPress-1>", x=row_x + 30, y=row_y + row_height // 2)
                app.tree.event_generate("<ButtonRelease-1>", x=row_x + 30, y=row_y + row_height // 2)
                app.update()
            settle()
            check("real list double-click toggles added valve and updates counts", valve(added_id)["opened"]
                  and f"전체 {initial_count + 1}" in app.counts.get())
            app.delete_selected()
            settle()
            check("delete removes selected valve and updates count", len(app.valves) == initial_count
                  and not any(row["id"] == added_id for row in app.valves) and f"전체 {initial_count}" in app.counts.get())
            app.editing.set(False)

            transparent = Image.new("RGBA", (6, 4), (20, 30, 40, 0))
            transparent.putpixel((2, 1), (40, 90, 140, 255))
            transparent_path = temp / "transparent-source.png"
            transparent.save(transparent_path)
            original_source_bytes = transparent_path.read_bytes()
            app.load_image(transparent_path)
            settle()
            check("transparent image uses white preserves colors and source bytes", app.background.mode == "RGB"
                  and app.background.getpixel((0, 0)) == (255, 255, 255)
                  and app.background.getpixel((2, 1)) == (40, 90, 140)
                  and transparent_path.read_bytes() == original_source_bytes)

            portrait = Image.new("RGB", (360, 720), "#ffffff")
            draw = ImageDraw.Draw(portrait)
            draw.rectangle((12, 12, 347, 707), outline="#2563eb", width=5)
            draw.rectangle((25, 25, 100, 90), fill="#fbbf24")
            source_image = temp / "different-aspect.png"
            portrait.save(source_image)
            app.load_image(source_image)
            settle()
            old_state = valve("V06")["opened"]
            click("V06")
            check("portrait image letterboxing preserves normalized click alignment", app.background.size == (360, 720)
                  and valve("V06")["opened"] != old_state)

            diagram = Image.new("RGB", (1600, 900), "white")
            diagram_draw = ImageDraw.Draw(diagram)
            for center in (160, 430):
                diagram_draw.line((center - 80, 200, center + 100, 200), fill="#8f949b", width=12)
                diagram_draw.rectangle((center - 15, 188, center + 15, 212), fill="#c6cbd1", outline="#60656b", width=2)
            diagram_draw.line((158, 177, 158, 200), fill="#60656b", width=5)
            diagram_draw.line((430, 177, 430, 200), fill="#60656b", width=5)
            diagram_draw.line((158, 177, 205, 177), fill="#16a34a", width=8)
            diagram_draw.line((430, 177, 430, 127), fill="#dc2626", width=8)
            diagram_draw.rounded_rectangle((490, 260, 560, 325), radius=8, fill="#16a34a")
            diagram_draw.ellipse((560, 35, 590, 65), fill="#dc2626")
            source_image = temp / "pictured-levers.png"
            diagram.save(source_image)
            fixture_bytes = source_image.read_bytes()
            app.load_image(source_image)
            settle()
            imported = sorted(app.valves, key=lambda row: row["x"])
            check("detector imports only elongated pictured levers and preserves source bytes", len(imported) == 2
                  and imported[0]["opened"] is True and imported[1]["opened"] is False
                  and all(row.get("visual", {}).get("body") is False for row in imported)
                  and app.background.getpixel((510, 290)) == diagram.getpixel((510, 290))
                  and source_image.read_bytes() == fixture_bytes and only_picture())
            pictured_id = imported[0]["id"]
            click(pictured_id)
            check("detected lever rotation removes the original color without a ghost", not valve(pictured_id)["opened"]
                  and lever_matches(valve(pictured_id))
                  and app.rendered_image.getpixel((185, 177)) == app.background.getpixel((185, 177))
                  and not is_color(app.rendered_image.getpixel((185, 177)), "green"))
            click(pictured_id)
            project = temp / "working.vcp"
            expected_valves = copy.deepcopy(app.valves)
            expected_pixels = app.background.tobytes()
            expected_render = app.rendered_image.tobytes()
            app.save_project(project)
            check("project save clears dirty and records path", not app.dirty and app.project_path == project.resolve())
            with zipfile.ZipFile(project) as archive:
                check("project embeds its background image", {"project.json", "background.png"}.issubset(archive.namelist()))
                document = json.loads(archive.read("project.json"))
                png = archive.read("background.png")
            relocated_dir = temp / "portable-copy"
            relocated_dir.mkdir()
            relocated = relocated_dir / "renamed.vcp"
            shutil.copy2(project, relocated)
            source_image.unlink()
            app.valves[0]["opened"] = not app.valves[0]["opened"]
            app.valves[0]["x"] = 0.02
            app.sync()
            app.load_project(relocated)
            settle()
            check("portable project reopens image positions properties and current states", app.valves == expected_valves
                  and app.background.tobytes() == expected_pixels and app.rendered_image.tobytes() == expected_render
                  and app.project_path == relocated.resolve())

            def write_project(path, data, background=png):
                with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("project.json", json.dumps(data, ensure_ascii=False))
                    if background is not None:
                        archive.writestr("background.png", background)

            future = copy.deepcopy(document)
            future["schema_version"] = 99
            path = temp / "future.vcp"
            write_project(path, future)
            check("unsupported project schema rejects without losing active project", expect_rejected(path, app.load_project))
            pixels = copy.deepcopy(document)
            pixels["coordinate_system"] = "pixels"
            path = temp / "pixels.vcp"
            write_project(path, pixels)
            check("wrong coordinate system rejects without losing active project", expect_rejected(path, app.load_project))
            path = temp / "missing-image.vcp"
            write_project(path, document, background=None)
            check("missing embedded image rejects without losing active project", expect_rejected(path, app.load_project))
            path = temp / "broken-image.vcp"
            write_project(path, document, background=b"not an image")
            check("corrupt embedded image rejects without losing active project", expect_rejected(path, app.load_project))
            path = temp / "broken-project.vcp"
            path.write_bytes(b"not a ZIP archive")
            check("corrupt project rejects without losing active project", expect_rejected(path, app.load_project))

            layout = temp / "layout.json"
            app.save_layout(layout)
            layout_data = json.loads(layout.read_text(encoding="utf-8"))
            check("layout export preserves positions but starts all valves closed", not any(v["opened"] for v in layout_data["valves"])
                  and layout_data["valves"][0]["x"] == app.valves[0]["x"])
            invalid = copy.deepcopy(layout_data)
            invalid["valves"][0]["x"] = 1.5
            bad_layout = temp / "invalid-layout.json"
            bad_layout.write_text(json.dumps(invalid), encoding="utf-8")
            check("invalid layout rejects without losing active project", expect_rejected(bad_layout, app.load_layout))
            enormous = copy.deepcopy(layout_data)
            enormous["valves"][0]["x"] = 10 ** 1000
            enormous_layout = temp / "enormous-coordinate-layout.json"
            enormous_layout.write_text(json.dumps(enormous), encoding="utf-8")
            check("enormous integer coordinate rejects without overflow or state loss", expect_rejected(enormous_layout, app.load_layout))
            bad_visual = copy.deepcopy(layout_data)
            bad_visual["valves"][0]["visual"] = dict(pivot_offset=[0, 0], length=-0.1, thickness=0.005, side=1, body=True)
            bad_visual_path = temp / "invalid-visual-layout.json"
            bad_visual_path.write_text(json.dumps(bad_visual), encoding="utf-8")
            check("invalid lever visual metadata rejects without losing active picture", expect_rejected(bad_visual_path, app.load_layout))
            state = temp / "state.json"
            app.export_state(state)
            state_data = json.loads(state.read_text(encoding="utf-8"))
            check("state export records actual simulation states", state_data["mode"] == "simulation"
                  and len(state_data["valves"]) == len(app.valves)
                  and all(row["state"] == ("OPEN" if valve(row["id"])["opened"] else "CLOSED") for row in state_data["valves"]))

            saved_bytes = relocated.read_bytes()
            before = snapshot()
            replacement_target = "valve_control.os.replace"
            failed = False
            with patch(replacement_target, side_effect=PermissionError("injected final replacement failure")):
                try:
                    app.save_project(relocated)
                except OSError:
                    failed = True
            check("atomic save failure preserves existing project and active state", failed
                  and relocated.read_bytes() == saved_bytes and snapshot() == before)

            app.dirty = True
            with patch.object(messagebox, "askyesnocancel", return_value=None):
                check("cancel discard preserves unsaved work", app.confirm_discard() is False and app.dirty)
                app.on_close()
                check("cancel close keeps the application alive", bool(app.winfo_exists()))
            with patch.object(messagebox, "askyesnocancel", return_value=False):
                check("explicit discard allows replacement or close", app.confirm_discard() is True)
            actual_path = app.project_path
            app.project_path = None
            with patch.object(messagebox, "askyesnocancel", return_value=True), \
                    patch.object(program.filedialog, "asksaveasfilename", return_value=""):
                check("cancel save dialog prevents discarding unsaved changes", app.confirm_discard() is False and app.dirty)
            app.project_path = actual_path
            with patch.object(messagebox, "askyesnocancel", return_value=True):
                check("save choice writes project before allowing replacement", app.confirm_discard() is True
                      and not app.dirty and app.project_path == actual_path)
            app.load_layout(layout)
            settle()
            check("saved layout imports with closed initial states", not any(row["opened"] for row in app.valves))
            legacy = copy.deepcopy(layout_data)
            for row in legacy["valves"]:
                row.pop("visual", None)
            legacy_path = temp / "legacy-layout.json"
            legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
            app.load_layout(legacy_path)
            settle()
            check("legacy schema without visual metadata loads as pictured valves", len(app.valves) == len(legacy["valves"])
                  and all(all(row[key] == saved[key] for key in ("id", "name", "x", "y", "axis", "opened"))
                          for row, saved in zip(app.valves, legacy["valves"])) and only_picture())
            empty = app.document([])
            empty_path = temp / "empty-layout.json"
            empty_path.write_text(json.dumps(empty), encoding="utf-8")
            app.load_layout(empty_path)
            settle()
            press(2, 2)
            check("zero-valve layout safely supports selection and canvas clicks", not app.valves
                  and app.selected is None and "전체 0" in app.counts.get())
            app.begin_add()
            probe = dict(x=0.5, y=0.5)
            press(*app.screen(probe))
            check("canvas add recovers from a zero-valve layout", len(app.valves) == 1 and app.selected == app.valves[0]["id"])
            check("all GUI callbacks completed without exceptions", not errors)

            result = {
                "status": "passed", "checks": checks, "count": len(checks),
                "python": platform.python_version(), "pillow": PIL.__version__,
                "tk": app.tk.call("package", "require", "Tk"),
                "screen_capture": ["implementation_closed.png", "implementation_open.png"],
                "original_attachment_tested": True,
                "reference_image_size": list(reference_size),
                "reference_valve_count": initial_count,
                "reference_open_count": initial_open_count,
            }
            (output / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Completed: {len(checks)} meaningful GUI checks passed", flush=True)
    finally:
        if app is not None:
            try:
                if app.winfo_exists():
                    app.destroy()
            except Exception:
                pass
        if display is not None:
            display.terminate()
            display.wait(timeout=5)
            os.environ.pop("DISPLAY", None)


if __name__ == "__main__":
    main()
