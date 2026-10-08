"""도면 속 밸브 손잡이의 색과 방향을 바꾸는 모식 제어. Python 3.11+."""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import datetime
import io
import json
import math
import os
import platform
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk
import zipfile

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageTk

import valve_render

GREEN, RED = "#16a34a", "#dc2626"
COORDINATES = "normalized_0_to_1"


def default_valves():
    rows = [
        (588, 248, "VS-1521 상부 출구", "horizontal"),
        (772, 248, "조절밸브 후단", "horizontal"),
        (936, 248, "상부 주배관 1", "horizontal"),
        (1157, 248, "상부 주배관 2", "horizontal"),
        (1330, 248, "DC-1523 출구", "horizontal"),
        (940, 96, "GC-1512B 상부 분기", "horizontal"),
        (1312, 172, "GC-1512B 중간 분기", "horizontal"),
        (444, 451, "GAS N2 탱크 유입", "vertical"),
        (506, 451, "VS-1521 상부 연결 1", "vertical"),
        (541, 451, "VS-1521 상부 연결 2", "vertical"),
        (726, 455, "바이패스 상단", "horizontal"),
        (822, 528, "압축기 유입", "horizontal"),
        (680, 576, "바이패스 세로 연결", "vertical"),
        (685, 668, "하부 주배관", "vertical"),
        (725, 751, "바이패스 하단", "horizontal"),
        (862, 835, "GC-1512B 하부 출구", "horizontal"),
        (492, 834, "VS-1521 드레인", "vertical"),
        (385, 705, "SR-1331 탱크 유입", "horizontal"),
        (242, 620, "SC-1811 세로 분기", "vertical"),
        (1250, 474, "압축기 상부 연결", "vertical"),
    ]
    initially_open = {1, 2, 3, 4, 5, 9, 10, 12, 13, 18, 19, 20}
    right_mount = {10, 19}
    left_lever = {8, 12, 18, 20}
    result = []
    for i, (x, y, n, a) in enumerate(rows, 1):
        offset = [0, -24 / 900] if a == "horizontal" else [(27 if i in right_mount else -27) / 1600, 0]
        result.append(dict(id=f"V{i:02}", name=n, x=x / 1600, y=y / 900, axis=a,
                           opened=i in initially_open,
                           visual=dict(pivot_offset=offset, length=52 / 1600,
                                       thickness=8 / 1600, side=-1 if i in left_lever else 1,
                                       body=True)))
    return result


def demo_image():
    image = Image.new("RGB", (1600, 900), "#f8fafc")
    d = ImageDraw.Draw(image)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 24)
    except OSError:
        f = ImageFont.load_default(size=24)
    pipes = [
        [(120, 383), (444, 383), (444, 510)], [(120, 546), (242, 546), (242, 705)],
        [(120, 705), (408, 705)], [(506, 500), (506, 248), (1455, 248)],
        [(875, 248), (875, 96), (1455, 96)], [(1250, 528), (1250, 172), (1455, 172)],
        [(541, 500), (541, 383), (625, 383), (625, 620), (680, 620)],
        [(680, 620), (680, 390), (774, 390), (774, 528), (980, 528)],
        [(680, 455), (747, 455)], [(685, 620), (685, 835), (1455, 835)],
        [(685, 751), (747, 751)], [(492, 790), (492, 862)], [(1080, 528), (1410, 528)],
    ]
    for points in pipes:
        d.line(points, fill="#64748b", width=16, joint="curve")
        d.line(points, fill="#cbd5e1", width=9, joint="curve")
    d.rounded_rectangle((408, 500, 576, 790), radius=65, fill="#e2e8f0", outline="#475569", width=4)
    d.rounded_rectangle((975, 552, 1455, 737), radius=24, fill="#c1e8cb", outline="#31834a", width=4)
    for x in (1025, 1265):
        d.rounded_rectangle((x, 577, x + 145, 676), radius=15, fill="#91cfa0", outline="#31834a", width=3)
    for x, y, text in [(40, 360, "GAS N2"), (40, 523, "SC-1811"), (40, 682, "SR-1331"),
                        (420, 630, "VS-1521"), (1110, 705, "GC-1512A"),
                        (1390, 62, "GC-1512B"), (1390, 138, "GC-1512B"),
                        (1400, 214, "DC-1523"), (1390, 800, "GC-1512B")]:
        d.text((x, y), text, font=f, fill="#0f172a")
    d.text((50, 40), "GC-1512A / DEMO - Open your source image", font=f, fill="#334155")
    return image


def validate(data):
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("지원하지 않는 파일 버전입니다.")
    if data.get("coordinate_system") != COORDINATES or data.get("mode", "simulation") != "simulation":
        raise ValueError("지원하지 않는 좌표계 또는 모드입니다.")
    rows, seen = data.get("valves"), set()
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("밸브 목록을 확인하세요. 최대 1,000개까지 지원합니다.")
    keys = {"id", "name", "x", "y", "axis", "opened"}
    for v in rows:
        if not isinstance(v, dict) or not keys.issubset(v) or set(v) - keys - {"visual"}:
            raise ValueError("밸브 항목 형식이 잘못되었습니다.")
        if any(not isinstance(v[k], str) or not v[k].strip() or len(v[k]) > 200 for k in ("id", "name")):
            raise ValueError("밸브 ID와 이름은 비어 있으면 안 됩니다.")
        if v["id"] in seen or v["axis"] not in ("horizontal", "vertical") or type(v["opened"]) is not bool:
            raise ValueError("중복 ID, 배관 방향 또는 상태를 확인하세요.")
        if not all(type(v[k]) in (int, float) and 0 <= v[k] <= 1 and math.isfinite(v[k]) for k in ("x", "y")):
            raise ValueError("밸브 좌표는 0~1 사이여야 합니다.")
        if "visual" in v:
            visual = v["visual"]
            required_visual = {"pivot_offset", "length", "thickness", "side", "body"}
            if not isinstance(visual, dict) or not required_visual.issubset(visual) or set(visual) - required_visual - {"artwork", "turn"}:
                raise ValueError("밸브 손잡이 정보가 잘못되었습니다.")
            offset = visual["pivot_offset"]
            if not isinstance(offset, list) or len(offset) != 2 or not all(type(n) in (int, float) and -0.25 <= n <= 0.25 and math.isfinite(n) for n in offset):
                raise ValueError("밸브 손잡이 축 위치를 확인하세요.")
            if not all(type(visual[k]) in (int, float) and 0 < visual[k] <= 0.25 and math.isfinite(visual[k]) for k in ("length", "thickness")) or visual["thickness"] > visual["length"]:
                raise ValueError("밸브 손잡이 크기를 확인하세요.")
            if type(visual["side"]) is not int or visual["side"] not in (-1, 1) or type(visual["body"]) is not bool:
                raise ValueError("밸브 손잡이 방향을 확인하세요.")
            if "turn" in visual and (type(visual["turn"]) is not int or visual["turn"] not in (-1, 1)):
                raise ValueError("손잡이 회전 방향을 확인하세요.")
            if "artwork" in visual:
                artwork = visual["artwork"]
                if not isinstance(artwork, dict) or set(artwork) != {"png", "size", "offset", "opened", "axis"}:
                    raise ValueError("원본 손잡이 이미지 형식을 확인하세요.")
                if type(artwork["opened"]) is not bool or artwork["axis"] not in ("horizontal", "vertical"):
                    raise ValueError("원본 손잡이 상태를 확인하세요.")
                for key, lower in (("size", 0), ("offset", -0.5)):
                    values = artwork[key]
                    if not isinstance(values, list) or len(values) != 2 or not all(type(n) in (int, float) and lower <= n <= 0.5 and math.isfinite(n) for n in values):
                        raise ValueError("원본 손잡이 이미지 위치를 확인하세요.")
                if min(artwork["size"]) <= 0 or not isinstance(artwork["png"], str) or len(artwork["png"]) > 150_000:
                    raise ValueError("원본 손잡이 이미지 크기를 확인하세요.")
                try:
                    data = base64.b64decode(artwork["png"], validate=True)
                    with Image.open(io.BytesIO(data)) as sprite:
                        if sprite.format != "PNG" or sprite.mode != "RGBA" or max(sprite.size) > 512:
                            raise ValueError("원본 손잡이 PNG를 확인하세요.")
                        sprite.verify()
                except (OSError, ValueError) as exc:
                    raise ValueError("원본 손잡이 PNG를 확인하세요.") from exc
        seen.add(v["id"])
    return deepcopy(rows)


def atomic_write(path, writer):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=".valve-", dir=path.parent)
    os.close(fd)
    try:
        writer(Path(tmp))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def initial_scene():
    """PDF에서 추출하고 손잡이 위치를 확인한 기본 도면을 읽는다."""
    path = Path(__file__).resolve().parent / "assets" / "GC-1512A.vcp"
    if not path.exists():
        return demo_image(), default_valves(), False
    with zipfile.ZipFile(path) as archive:
        rows = validate(json.loads(archive.read("project.json")))
        with Image.open(io.BytesIO(archive.read("background.png"))) as image:
            background = image.convert("RGB")
    return background, rows, True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1460x900")
        self.minsize(1080, 760)
        families = set(tkfont.families(self))
        family = next((f for f in ("맑은 고딕", "Malgun Gothic", "Noto Sans CJK KR", "AppleGothic") if f in families), "TkDefaultFont")
        if family != "TkDefaultFont":
            tkfont.nametofont("TkDefaultFont").configure(family=family, size=10)
        self.ui_font = (family, 10)
        self.background, self.valves, self.reference_loaded = initial_scene()
        self.selected, self.drag_id, self.adding = "V01", None, False
        self.project_path, self.dirty, self.pending = None, False, None
        self.photo, self.cached_photo, self.cached_size = None, None, None
        self.rendered_image, self.scene_key = None, None
        self.transform = (0., 0., 1600., 900.)
        self.editing, self.show_ids = tk.BooleanVar(), tk.BooleanVar(value=False)
        self.id_var, self.name_var, self.axis_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.status, self.counts = tk.StringVar(), tk.StringVar()
        self.build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Control-s>", lambda e: self.save_dialog())
        self.bind("<Control-o>", lambda e: self.open_dialog())
        self.bind("<Escape>", lambda e: self.cancel_add())
        self.sync()
        self.mode_changed()

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=(7, 6))
        style.configure("Treeview", font=self.ui_font, rowheight=29)
        menu, file_menu = tk.Menu(self), tk.Menu(self, tearoff=False)
        for name, action in [("기본 도면 열기", self.reference_dialog), ("이미지 열기", self.image_dialog), ("프로젝트 열기", self.open_dialog),
                             ("프로젝트 저장", self.save_dialog), ("다른 이름으로 저장", lambda: self.save_dialog(True)),
                             ("배치 JSON 불러오기", lambda: self.json_dialog("load")),
                             ("배치 JSON 저장 (초기 상태 닫힘)", lambda: self.json_dialog("layout")),
                             ("현재 상태 JSON 내보내기", lambda: self.json_dialog("state")), ("종료", self.on_close)]:
            file_menu.add_command(label=name, command=action)
        menu.add_cascade(label="파일", menu=file_menu)
        self.config(menu=menu)
        top = tk.Frame(self, bg="#102a3c", padx=18, pady=13)
        top.pack(fill="x")
        tk.Label(top, text="GC-1512A  |  밸브 모식 제어", font=(self.ui_font[0], 18, "bold"), bg="#102a3c", fg="white").pack(side="left")
        tk.Label(top, text="상태 시뮬레이션", bg="#102a3c", fg="#fbbf24", font=self.ui_font).pack(side="right")
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")
        for text, action in [("기본 도면", self.reference_dialog), ("이미지 열기", self.image_dialog), ("프로젝트 열기", self.open_dialog), ("저장", self.save_dialog)]:
            ttk.Button(bar, text=text, command=action).pack(side="left", padx=3)
        ttk.Checkbutton(bar, text="위치 편집", variable=self.editing, command=self.mode_changed).pack(side="left", padx=12)
        ttk.Checkbutton(bar, text="편집 시 ID 표시", variable=self.show_ids, command=self.draw).pack(side="left")
        ttk.Label(bar, textvariable=self.counts).pack(side="right")
        body = ttk.Frame(self, padding=(12, 0, 12, 8))
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg="#e2e8f0", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        side = ttk.Frame(body, width=320, padding=(12, 0, 0, 0))
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="밸브 상태 · 목록 더블클릭으로 전환", font=self.ui_font).pack(anchor="w", pady=5)
        frame = ttk.Frame(side)
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("name", "state"), show="tree headings", height=6)
        for key, label, width in [("#0", "ID", 48), ("name", "위치 / 설명", 178), ("state", "상태", 62)]:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, stretch=key == "name")
        scrollbar = ttk.Scrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("open", foreground=GREEN)
        self.tree.tag_configure("closed", foreground=RED)
        self.tree.bind("<<TreeviewSelect>>", self.select)
        self.tree.bind("<Double-1>", self.list_toggle)
        self.tree.bind("<space>", lambda e: self.toggle())
        id_editor = ttk.Frame(side)
        id_editor.pack(fill="x", pady=(10, 4))
        ttk.Label(id_editor, text="밸브 ID", font=self.ui_font).pack(side="left", padx=(0, 8))
        ttk.Entry(id_editor, textvariable=self.id_var).pack(side="left", fill="x", expand=True)
        ttk.Label(side, text="설명 / 위치 이름", font=self.ui_font).pack(anchor="w", pady=(2, 3))
        ttk.Entry(side, textvariable=self.name_var).pack(fill="x")
        props = ttk.Frame(side)
        props.pack(fill="x", pady=5)
        ttk.Combobox(props, textvariable=self.axis_var, values=("horizontal", "vertical"), state="readonly", width=12).pack(side="left")
        ttk.Button(props, text="변경 적용", command=lambda: self.guard(self.apply_properties)).pack(side="right")
        actions = ttk.Frame(side)
        actions.pack(fill="x", pady=3)
        ttk.Button(actions, text="밸브 추가", command=self.begin_add).pack(side="left")
        ttk.Button(actions, text="삭제", command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(actions, text="개폐 전환", command=self.toggle).pack(side="right")
        legend = ttk.Frame(side)
        legend.pack(fill="x", pady=8)
        ttk.Label(legend, text="● 열림", foreground=GREEN).pack(side="left")
        ttk.Label(legend, text="  ● 닫힘", foreground=RED).pack(side="left")
        ttk.Label(side, text="조작 이력").pack(anchor="w")
        self.log = tk.Listbox(side, height=5, font=self.ui_font, relief="flat")
        self.log.pack(fill="x", pady=5)
        ttk.Label(self, textvariable=self.status, padding=(12, 8)).pack(fill="x")
        self.canvas.bind("<Configure>", self.schedule)
        self.canvas.bind("<ButtonPress-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag_id", None))

    def current(self):
        return next((v for v in self.valves if v["id"] == self.selected), None)

    def mark_dirty(self):
        self.dirty = True
        self.update_title()

    def update_title(self):
        name = self.project_path.name if self.project_path else "새 프로젝트"
        self.title(f"{'* ' if self.dirty else ''}{name} | 밸브 모식 제어")

    def sync(self):
        ids = {v["id"] for v in self.valves}
        for item in self.tree.get_children():
            if item not in ids:
                self.tree.delete(item)
        for index, v in enumerate(self.valves):
            fields = dict(text=v["id"], values=(v["name"], "열림" if v["opened"] else "닫힘"), tags=("open" if v["opened"] else "closed",))
            if self.tree.exists(v["id"]):
                self.tree.item(v["id"], **fields)
            else:
                self.tree.insert("", "end", iid=v["id"], **fields)
            self.tree.move(v["id"], "", index)
        if self.selected not in ids:
            self.selected = self.valves[0]["id"] if self.valves else None
        if self.selected:
            self.tree.selection_set(self.selected)
        v = self.current()
        self.id_var.set(v["id"] if v else "")
        self.name_var.set(v["name"] if v else "")
        self.axis_var.set(v["axis"] if v else "horizontal")
        n = sum(v["opened"] for v in self.valves)
        self.counts.set(f"전체 {len(self.valves)}  |  열림 {n}  |  닫힘 {len(self.valves) - n}")
        self.update_title()
        self.schedule()

    def schedule(self, event=None):
        if self.pending:
            self.after_cancel(self.pending)
        self.pending = self.after(20, self.draw)

    def draw(self):
        if self.pending:
            self.after_cancel(self.pending)
            self.pending = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2:
            return
        scale = min(w / self.background.width, h / self.background.height)
        iw, ih = max(1, round(self.background.width * scale)), max(1, round(self.background.height * scale))
        self.transform = ((w - iw) / 2, (h - ih) / 2, iw, ih)
        scene_key = (id(self.background), json.dumps(self.valves, sort_keys=True))
        if self.scene_key != scene_key:
            self.rendered_image = valve_render.render_scene(self.background, self.valves)
            self.scene_key, self.cached_size = scene_key, None
        if self.cached_size != (iw, ih):
            self.cached_photo = ImageTk.PhotoImage(self.rendered_image.resize((iw, ih), Image.Resampling.LANCZOS))
            self.cached_size = (iw, ih)
        self.photo = self.cached_photo
        ox, oy, _, _ = self.transform
        self.canvas.delete("all")
        self.canvas.create_image(ox, oy, image=self.photo, anchor="nw", tags="background")
        if self.editing.get():
            for v in self.valves:
                x, y = self.screen(v)
                if v["id"] == self.selected:
                    x0, y0, x1, y1 = valve_render.visual_bounds(self.background, v)
                    sx, sy = iw / self.background.width, ih / self.background.height
                    self.canvas.create_rectangle(ox + x0 * sx, oy + y0 * sy, ox + x1 * sx, oy + y1 * sy,
                                                 outline="#2563eb", width=2, dash=(3, 3))
                if self.show_ids.get():
                    self.canvas.create_text(x, y + 25, text=v["id"], fill="#334155", font=self.ui_font)

    def screen(self, v):
        ox, oy, iw, ih = self.transform
        return ox + v["x"] * iw, oy + v["y"] * ih

    def normalized(self, x, y):
        ox, oy, iw, ih = self.transform
        return ((x - ox) / iw, (y - oy) / ih) if ox <= x <= ox + iw and oy <= y <= oy + ih else None

    def hit(self, x, y):
        if not self.valves or self.normalized(x, y) is None:
            return None
        nx, ny = self.normalized(x, y)
        px, py = nx * self.background.width, ny * self.background.height
        candidates = [v for v in self.valves if valve_render.valve_hit(self.background, v, px, py)]
        return min(candidates, key=lambda v: math.hypot(x - self.screen(v)[0], y - self.screen(v)[1])) if candidates else None

    def select(self, event=None):
        rows = self.tree.selection()
        if rows and rows[0] != self.selected:
            self.selected = rows[0]
            self.sync()

    def list_toggle(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.selected = item
            self.sync()
            self.toggle()
        return "break"

    def toggle(self, valve_id=None):
        if self.editing.get():
            self.status.set("위치 편집을 끄면 개폐 전환할 수 있습니다.")
            return
        v = next((v for v in self.valves if v["id"] == (valve_id or self.selected)), None)
        if v:
            v["opened"] = not v["opened"]
            text = f"{v['id']} · {v['name']}: {'열림' if v['opened'] else '닫힘'}"
            self.log.insert(0, f"{datetime.now().astimezone():%H:%M:%S}  {text}")
            if self.log.size() > 100:
                self.log.delete(100, "end")
            self.status.set(text)
            self.mark_dirty()
            self.sync()

    def press(self, event):
        if self.adding:
            self.guard(lambda: self.new_valve(event.x, event.y))
            return
        v = self.hit(event.x, event.y)
        if v:
            self.selected = v["id"]
            self.sync()
            self.tree.see(v["id"])
            if self.editing.get():
                self.drag_id = v["id"]
            else:
                self.toggle()
        elif self.editing.get() and self.current():
            self.move(self.current(), event.x, event.y)

    def move(self, v, x, y):
        position = self.normalized(x, y)
        if position and position != (v["x"], v["y"]):
            v["x"], v["y"] = position
            self.mark_dirty()
            self.draw()

    def drag(self, event):
        if self.editing.get() and self.drag_id:
            v = next((v for v in self.valves if v["id"] == self.drag_id), None)
            if v:
                self.move(v, event.x, event.y)

    def mode_changed(self):
        self.adding, self.drag_id = False, None
        self.status.set("위치 편집: 선택 후 드래그 또는 배경 클릭으로 이동" if self.editing.get() else "밸브 몸체·손잡이 클릭: 녹색·배관과 나란함(열림) ↔ 빨강·배관과 직각(닫힘)")

    def begin_add(self):
        self.editing.set(True)
        self.adding = True
        self.status.set("새 밸브를 놓을 위치를 클릭하세요. Esc로 취소합니다.")

    def cancel_add(self):
        self.mode_changed()

    def new_valve(self, x, y):
        position = self.normalized(x, y)
        if position is None:
            return
        if len(self.valves) >= 1000:
            raise ValueError("최대 1,000개까지 지원합니다.")
        ids, n = {v["id"] for v in self.valves}, 1
        while f"V{n:02}" in ids:
            n += 1
        self.selected = f"V{n:02}"
        self.valves.append(dict(id=self.selected, name="새 밸브", x=position[0], y=position[1], axis="horizontal", opened=False))
        self.adding = False
        self.mark_dirty()
        self.sync()
        self.status.set(f"{self.selected} 추가됨 · 이름과 방향을 지정하세요.")

    def delete_selected(self):
        v = self.current()
        if v and messagebox.askyesno("밸브 삭제", f"{v['id']} · {v['name']}를 삭제할까요?", parent=self):
            self.valves.remove(v)
            self.selected, self.drag_id = None, None
            self.mark_dirty()
            self.sync()

    def apply_properties(self):
        v, name, axis = self.current(), self.name_var.get().strip(), self.axis_var.get()
        if not v:
            return
        identifier = self.id_var.get().strip()
        if not identifier or len(identifier) > 200:
            raise ValueError("밸브 ID는 1~200자로 입력하세요.")
        if any(row is not v and row["id"] == identifier for row in self.valves):
            raise ValueError("이미 사용 중인 밸브 ID입니다. 다른 ID를 입력하세요.")
        if not name or len(name) > 200 or axis not in ("horizontal", "vertical"):
            raise ValueError("설명(1~200자)과 배관 방향을 확인하세요.")
        if (v["id"], v["name"], v["axis"]) != (identifier, name, axis):
            if axis != v["axis"] and "visual" in v and "artwork" not in v["visual"]:
                dx, dy = v["visual"]["pivot_offset"]
                distance = max(abs(dx * self.background.width), abs(dy * self.background.height))
                v["visual"]["pivot_offset"] = [0, -distance / self.background.height] if axis == "horizontal" else [-distance / self.background.width, 0]
            previous_id = v["id"]
            v["id"], v["name"], v["axis"] = identifier, name, axis
            self.selected = identifier
            if self.drag_id == previous_id:
                self.drag_id = identifier
            if previous_id != identifier:
                self.log.insert(0, f"{datetime.now().astimezone():%H:%M:%S}  ID 변경: {previous_id} → {identifier}")
            self.mark_dirty()
            self.sync()

    def load_image(self, path):
        with Image.open(path) as image:
            rgba = ImageOps.exif_transpose(image).convert("RGBA")
            loaded = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
        clean, detected = valve_render.prepare_image(loaded)
        self.background, self.cached_size = clean, None
        if detected:
            self.valves, self.selected = detected, detected[0]["id"]
            self.sync()
        self.mark_dirty()
        self.draw()
        self.status.set(f"{Path(path).name} · 녹색·빨간색 손잡이 {len(detected)}개 인식 · 원본 상태 적용 · 위치 편집으로 확인하세요."
                        if detected else f"배경: {Path(path).name} · 인식된 손잡이 없음 · 위치 편집으로 밸브를 맞추세요.")

    def document(self, rows=None):
        return dict(schema_version=1, coordinate_system=COORDINATES, mode="simulation", valves=deepcopy(self.valves if rows is None else rows))

    def save_project(self, path):
        data, png = self.document(), io.BytesIO()
        validate(data)
        self.background.save(png, format="PNG")
        def write(temp):
            with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("project.json", json.dumps(data, ensure_ascii=False, indent=2))
                z.writestr("background.png", png.getvalue())
        atomic_write(path, write)
        self.project_path, self.dirty = Path(path).resolve(), False
        self.update_title()
        self.status.set(f"프로젝트 저장됨: {Path(path).name} · 배경, 배치, 현재 상태 포함")

    def load_project(self, path):
        with zipfile.ZipFile(path) as z:
            if set(z.namelist()) != {"project.json", "background.png"} or len(z.infolist()) != 2:
                raise ValueError("프로젝트의 이미지 또는 설정 파일이 없거나 중복되었습니다.")
            if z.getinfo("project.json").file_size > 2_000_000 or z.getinfo("background.png").file_size > 64_000_000:
                raise ValueError("프로젝트 파일 크기 제한을 초과했습니다.")
            rows = validate(json.loads(z.read("project.json")))
            with Image.open(io.BytesIO(z.read("background.png"))) as image:
                background = ImageOps.exif_transpose(image).convert("RGB")
        self.background, self.valves, self.cached_size = background, rows, None
        self.project_path, self.dirty = Path(path).resolve(), False
        self.selected = rows[0]["id"] if rows else None
        self.mode_changed()
        self.log.delete(0, "end")
        self.sync()
        self.status.set(f"프로젝트 복원됨: {Path(path).name} · 저장 당시 상태 적용")

    def save_layout(self, path):
        rows = [{**v, "opened": False} for v in self.valves]
        text = json.dumps(self.document(rows), ensure_ascii=False, indent=2)
        atomic_write(path, lambda p: p.write_text(text, encoding="utf-8"))

    def load_layout(self, path):
        rows = validate(json.loads(Path(path).read_text(encoding="utf-8")))
        self.valves, self.selected = rows, rows[0]["id"] if rows else None
        self.mode_changed()
        self.mark_dirty()
        self.sync()

    def export_state(self, path):
        data = dict(mode="simulation", exported_at=datetime.now().astimezone().isoformat(),
                    valves=[dict(id=v["id"], name=v["name"], state="OPEN" if v["opened"] else "CLOSED") for v in self.valves])
        atomic_write(path, lambda p: p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"))

    def image_dialog(self):
        path = filedialog.askopenfilename(parent=self, title="배경 이미지", filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp *.webp"), ("모든 파일", "*")])
        if path and self.confirm_discard():
            self.guard(lambda: self.load_image(path))

    def reference_dialog(self):
        if not self.confirm_discard():
            return
        background, rows, reference = initial_scene()
        if not reference:
            messagebox.showerror("기본 도면 없음", "내장 도면 파일을 확인하세요.", parent=self)
            return
        self.background, self.valves, self.reference_loaded = background, rows, True
        self.selected, self.project_path, self.dirty = rows[0]["id"], None, False
        self.editing.set(False)
        self.log.delete(0, "end")
        self.mode_changed()
        self.sync()
        self.status.set("원본 도면의 밸브 위치와 초기 상태를 불러왔습니다.")

    def save_dialog(self, save_as=False):
        path = None if save_as else self.project_path
        if not path:
            path = filedialog.asksaveasfilename(parent=self, title="현재 상태를 포함한 프로젝트 저장", defaultextension=".vcp", filetypes=[("밸브 프로젝트", "*.vcp")])
        return bool(path) and self.guard(lambda: self.save_project(path))

    def open_dialog(self):
        path = filedialog.askopenfilename(parent=self, title="프로젝트 열기", filetypes=[("밸브 프로젝트", "*.vcp")])
        if path and self.confirm_discard():
            self.guard(lambda: self.load_project(path))

    def json_dialog(self, action):
        if action == "load":
            path = filedialog.askopenfilename(parent=self, filetypes=[("밸브 배치 JSON", "*.json")])
            if path and self.confirm_discard():
                self.guard(lambda: self.load_layout(path))
        else:
            path = filedialog.asksaveasfilename(parent=self, initialfile="layout.json" if action == "layout" else "state.json", defaultextension=".json")
            if path:
                self.guard(lambda: self.save_layout(path) if action == "layout" else self.export_state(path))

    def confirm_discard(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel("미저장 변경", "변경 내용을 프로젝트로 저장할까요?\n예: 저장 / 아니요: 변경 버림 / 취소: 계속 작업", parent=self)
        return self.save_dialog() if answer is True else answer is False

    def on_close(self):
        if self.confirm_discard():
            self.destroy()

    def guard(self, action):
        try:
            action()
            return True
        except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, Image.DecompressionBombError, NotImplementedError, RuntimeError) as exc:
            messagebox.showerror("처리 오류", str(exc), parent=self)
            return False


def run_smoke(app, path):
    """배포 빌드의 실제 GUI·이미지·프로젝트 동작을 검증한다."""
    checks = []
    try:
        app.update()
        app.draw()
        assert app.reference_loaded and len(app.valves) >= 20
        assert any(v["opened"] for v in app.valves) and any(not v["opened"] for v in app.valves)
        assert all(app.canvas.type(item) == "image" for item in app.canvas.find_all())
        checks.append("mixed default states and image-only canvas")
        assets = Path(__file__).resolve().parent / "assets"
        with Image.open(assets / "GC-1512A.png") as original:
            assert ImageChops.difference(original.convert("RGB"), app.rendered_image).getbbox() is None
        checks.append("initial original artwork is pixel-identical")
        registry = json.loads((assets / "registration.json").read_text(encoding="utf-8"))
        assert len(registry["valves"]) == len(app.valves) == 20
        assert not any(row["id"] == "V21" for row in app.valves)
        before = deepcopy(app.valves)
        for point in registry["valves"]:
            ox, oy, iw, ih = app.transform
            cx = ox + point["body"][0] / registry["image_size"][0] * iw
            cy = oy + point["body"][1] / registry["image_size"][1] * ih
            for _ in range(2):
                previous = {row["id"]: row["opened"] for row in app.valves}
                app.canvas.event_generate("<ButtonPress-1>", x=round(cx), y=round(cy))
                app.canvas.event_generate("<ButtonRelease-1>", x=round(cx), y=round(cy))
                app.update()
                app.draw()
                assert [row["id"] for row in app.valves if row["opened"] != previous[row["id"]]] == [point["id"]]
        assert app.valves == before
        checks.append("all twenty actual source body coordinates click independently")
        v = next(v for v in app.valves if not v["opened"] and v["axis"] == "horizontal")
        x, y = app.screen(v)
        for opened in (True, False):
            app.canvas.event_generate("<ButtonPress-1>", x=round(x), y=round(y))
            app.canvas.event_generate("<ButtonRelease-1>", x=round(x), y=round(y))
            app.update()
            app.draw()
            assert v["opened"] is opened
            x0, y0, x1, y1 = valve_render.visual_bounds(app.background, v)
            crop = app.rendered_image.crop((int(x0), int(y0), math.ceil(x1), math.ceil(y1)))
            pixels = crop.load()
            points = [(cx, cy) for cy in range(crop.height) for cx in range(crop.width)
                      if (pixels[cx, cy][1] > 75 and pixels[cx, cy][1] > pixels[cx, cy][0] * 1.5 and pixels[cx, cy][1] > pixels[cx, cy][2] * 1.25)
                      or (pixels[cx, cy][0] > 100 and pixels[cx, cy][0] > pixels[cx, cy][1] * 1.5 and pixels[cx, cy][0] > pixels[cx, cy][2] * 1.5)]
            assert points
            width = max(p[0] for p in points) - min(p[0] for p in points)
            height = max(p[1] for p in points) - min(p[1] for p in points)
            assert (width > height * 2) if opened else (height > width * 2)
            checks.append("pictured lever opens green parallel" if opened else "pictured lever closes red perpendicular")
        previous_id, previous_row, previous_pixels = v["id"], deepcopy(v), app.rendered_image.tobytes()
        app.id_var.set("USER-VALVE-001")
        app.name_var.set("사용자 설명 확인")
        app.apply_properties()
        app.update()
        app.draw()
        assert v["id"] == "USER-VALVE-001" and v["name"] == "사용자 설명 확인"
        assert all(v[key] == previous_row[key] for key in ("x", "y", "axis", "opened", "visual"))
        assert app.rendered_image.tobytes() == previous_pixels
        assert app.tree.exists(v["id"]) and not app.tree.exists(previous_id)
        before_duplicate = deepcopy(app.valves)
        app.id_var.set(next(row["id"] for row in app.valves if row is not v))
        try:
            app.apply_properties()
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate valve ID was accepted")
        assert app.valves == before_duplicate
        app.id_var.set(v["id"])
        checks.append("user ID and description edits preserve geometry and reject duplicate IDs")
        with tempfile.TemporaryDirectory(prefix="valve-smoke-") as folder:
            image = Path(folder) / "image.png"
            rgba = Image.new("RGBA", (240, 180), (0, 0, 0, 0))
            rgba.putpixel((10, 10), (22, 163, 74, 255))
            rgba.save(image)
            app.load_image(image)
            assert app.background.getpixel((0, 0)) == (255, 255, 255)
            assert app.background.getpixel((10, 10)) == (22, 163, 74)
            checks.append("Pillow PNG decoding and transparency")
            app.toggle(v["id"])
            expected = deepcopy(app.valves)
            pixels = app.background.tobytes()
            project = Path(folder) / "project.vcp"
            app.save_project(project)
            app.valves = []
            app.load_project(project)
            assert app.valves == expected and app.background.tobytes() == pixels
            checks.append("embedded image and state project roundtrip")
        result = dict(status="passed", checks=checks, count=len(checks),
                      platform=platform.system(), python=platform.python_version(),
                      tk=app.tk.call("package", "require", "Tk"),
                      frozen=bool(getattr(sys, "frozen", False)))
        atomic_write(path, lambda p: p.write_text(json.dumps(result, indent=2), encoding="utf-8"))
        return 0
    except Exception as exc:
        result = dict(status="failed", checks=checks, count=len(checks),
                      platform=platform.system(), frozen=bool(getattr(sys, "frozen", False)),
                      error=f"{type(exc).__name__}: {exc}")
        atomic_write(path, lambda p: p.write_text(json.dumps(result, indent=2), encoding="utf-8"))
        return 1
    finally:
        app.destroy()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path)
    p.add_argument("--layout", type=Path)
    p.add_argument("--project", type=Path)
    p.add_argument("--smoke-test", type=Path, help=argparse.SUPPRESS)
    a = p.parse_args()
    if a.project and (a.image or a.layout):
        p.error("--project는 --image/--layout과 함께 사용하지 않습니다.")
    app = None
    try:
        app = App()
        if a.project:
            app.load_project(a.project)
        else:
            if a.image:
                app.load_image(a.image)
            if a.layout:
                app.load_layout(a.layout)
        if a.smoke_test:
            result = run_smoke(app, a.smoke_test)
            app = None
            return result
        else:
            app.mainloop()
    except (tk.TclError, OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, Image.DecompressionBombError, NotImplementedError, RuntimeError) as exc:
        if app is not None:
            app.destroy()
        if a.smoke_test:
            error = dict(status="failed", platform=platform.system(),
                         frozen=bool(getattr(sys, "frozen", False)),
                         error=f"{type(exc).__name__}: {exc}")
            atomic_write(a.smoke_test, lambda path: path.write_text(json.dumps(error), encoding="utf-8"))
            return 1
        p.exit(1, f"실행 오류: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
