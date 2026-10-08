"""Build and verify the Windows release on a native Windows CI runner.

Only the standard library is imported here so dependency failures can still
produce a small, machine-readable build report. Application tests run in
separate processes, including the actual frozen executable.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
RELEASE_VERSION = "1.1.0"
ARCHIVE_NAME = f"valve-control-windows-{RELEASE_VERSION}.zip"
MINIMUM_GUI_CHECKS = 40
REQUIRED_GUI_PROOFS = {
    "normal canvas contains only the rendered diagram image",
    "horizontal pictured lever closes red and perpendicular on real click",
    "horizontal pictured lever opens green and parallel on second click",
    "vertical pictured lever closes red and perpendicular to vertical pipe",
    "detector imports only elongated pictured levers and preserves source bytes",
    "detected lever rotation removes the original color without a ghost",
}
REQUIRED_PILLOW = "12.3.0"
REQUIRED_PYINSTALLER = "6.22.3"
PHASES = ("dependencies", "gui", "launcher", "build", "exe_smoke", "package")


class BuildFailure(RuntimeError):
    pass


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_passed(path: Path, *, frozen: bool | None = None) -> dict:
    if not path.is_file():
        raise BuildFailure(f"Expected validation output is missing: {path.name}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("status") != "passed":
        raise BuildFailure(f"Validation did not pass: {path.name}: {str(result.get('error', 'no diagnostic'))[:350]}")
    if frozen is not None:
        if result.get("platform") != "Windows" or result.get("frozen") is not frozen:
            raise BuildFailure(f"Expected native Windows/frozen={frozen} proof: {path.name}")
        if not isinstance(result.get("checks"), list) or not result["checks"]:
            raise BuildFailure(f"Validation contains no actual checks: {path.name}")
    return result


def run(command: list[str], *, cwd: Path, timeout: int) -> None:
    print("RUN:", subprocess.list2cmdline(command), flush=True)
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    try:
        transcript, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=20,
            )
        else:
            process.kill()
        transcript, _ = process.communicate(timeout=20)
        if transcript:
            print(transcript, flush=True)
        raise BuildFailure(f"Command timed out after {timeout}s: {Path(command[0]).name}") from None
    if transcript:
        print(transcript, flush=True)
    if process.returncode:
        # These commands contain no secrets. Save the final exception or native
        # startup error, without publishing whole CI logs or the environment.
        ending = " | ".join(line.strip() for line in transcript.splitlines()[-5:] if line.strip()) or "No diagnostic output"
        raise BuildFailure(f"Command exited {process.returncode}: {Path(command[0]).name}: {ending[:350]}")


def run_smoke(command: list[str], *, cwd: Path, timeout: int, result_path: Path, frozen: bool) -> dict:
    try:
        run(command, cwd=cwd, timeout=timeout)
    except BuildFailure:
        # A windowed EXE has no console stream. The application deliberately
        # writes its startup/test failure to JSON so this report remains useful.
        if result_path.is_file():
            read_passed(result_path, frozen=frozen)
        raise
    return read_passed(result_path, frozen=frozen)


def file_details(path: Path) -> dict:
    return {"name": path.name, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def base_status(args) -> dict:
    return {
        "schema_version": 1,
        "status": "running",
        "version": RELEASE_VERSION,
        "source_commit": args.source_sha,
        "run_url": args.run_url,
        "runner": {"platform": platform.system(), "architecture": platform.machine(),
                   "python": platform.python_version()},
        "phases": {name: {"status": "pending"} for name in PHASES},
    }


def build(args) -> int:
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # A failed rerun must never leave a previous successful package beside its
    # new failure report. Only the newly tested binary is eligible for delivery.
    (output / ARCHIVE_NAME).unlink(missing_ok=True)
    (output / "validation.json").unlink(missing_ok=True)
    status_path = output / "windows-build.json"
    status = base_status(args)
    phase = "dependencies"
    write_json(status_path, status)
    try:
        if sys.platform != "win32" or sys.maxsize <= 2 ** 32:
            raise BuildFailure("The release must be built and tested on native 64-bit Windows")
        if sys.version_info[:2] != (3, 13):
            raise BuildFailure("The release requires the pinned Python 3.13 runtime")
        versions = {"pillow": version("Pillow"), "pyinstaller": version("PyInstaller")}
        if versions != {"pillow": REQUIRED_PILLOW, "pyinstaller": REQUIRED_PYINSTALLER}:
            raise BuildFailure("Installed release dependencies do not match the pinned versions")
        status["phases"][phase] = {"status": "passed", **versions}

        phase = "gui"
        gui_file = HERE / "artifacts" / "validation.json"
        gui_file.unlink(missing_ok=True)
        run([sys.executable, "verify_gui.py"], cwd=HERE, timeout=180)
        gui_result = read_passed(gui_file)
        count = gui_result.get("count")
        checks = gui_result.get("checks")
        if type(count) is not int or count < MINIMUM_GUI_CHECKS or not isinstance(checks, list) or len(checks) != count:
            raise BuildFailure(f"Expected at least {MINIMUM_GUI_CHECKS} meaningful GUI checks with matching reported count")
        if not REQUIRED_GUI_PROOFS.issubset(checks):
            missing = sorted(REQUIRED_GUI_PROOFS.difference(checks))
            raise BuildFailure("Missing pictured-valve integration proofs: " + "; ".join(missing))
        status["phases"][phase] = {"status": "passed", "count": gui_result["count"]}

        phase = "launcher"
        launcher_file = HERE / "launcher-smoke.json"
        launcher_file.unlink(missing_ok=True)
        try:
            launcher_result = run_smoke(
                ["cmd.exe", "/d", "/c", "run_windows.cmd", "--smoke-test", launcher_file.name],
                cwd=HERE, timeout=300, result_path=launcher_file, frozen=False,
            )
        finally:
            launcher_file.unlink(missing_ok=True)
        status["phases"][phase] = {"status": "passed", "checks": launcher_result["checks"]}

        phase = "build"
        build_command = [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--onefile", "--windowed", "--name", "ValveControl", "--collect-all", "PIL",
            "--hidden-import", "valve_render",
            "--distpath", str(output / "dist"), "--workpath", str(output / "work"),
            "--specpath", str(output / "spec"),
        ]
        # Rendering is normally imported directly and generated from Python.
        # Retain an optional local asset directory if the release supplies one.
        assets = HERE / "assets"
        if assets.is_dir():
            build_command.extend(["--add-data", f"{assets}:assets"])
        build_command.append(str(HERE / "valve_control.py"))
        run(build_command, cwd=HERE, timeout=600)
        executable = output / "dist" / "ValveControl.exe"
        if not executable.is_file() or executable.stat().st_size < 1_000_000:
            raise BuildFailure("PyInstaller did not produce the expected standalone executable")
        status["phases"][phase] = {"status": "passed", **file_details(executable)}

        phase = "exe_smoke"
        # Run away from the source tree, in a path matching common Korean Windows
        # download locations. The one-file application must supply its own assets.
        with tempfile.TemporaryDirectory(prefix="ValveControl Windows ") as temporary:
            launch_dir = Path(temporary) / "한글 폴더"
            launch_dir.mkdir()
            launch_executable = launch_dir / "ValveControl.exe"
            shutil.copy2(executable, launch_executable)
            smoke_file = launch_dir / "exe-smoke.json"
            exe_result = run_smoke(
                [str(launch_executable), "--smoke-test", str(smoke_file)],
                cwd=launch_dir, timeout=120, result_path=smoke_file, frozen=True,
            )
        status["phases"][phase] = {"status": "passed", "checks": exe_result["checks"],
                                   "unicode_path": True, "space_in_path": True}

        phase = "package"
        validation = {"status": "passed", "platform": "Windows", "version": RELEASE_VERSION,
                      "source_commit": args.source_sha, "run_url": args.run_url,
                      "gui": gui_result, "launcher": launcher_result, "executable": exe_result,
                      "bundled_executable": file_details(executable)}
        validation_file = output / "validation.json"
        write_json(validation_file, validation)
        instructions = (
            f"Valve Control {RELEASE_VERSION} - Windows 10/11 (64-bit)\r\n\r\n"
            "ZIP을 폴더에 모두 압축 해제한 다음 ValveControl.exe를 더블 클릭하세요.\r\n"
            "Python 설치나 CMD 실행은 필요하지 않습니다.\r\n"
            "처음 시작할 때 단일 EXE가 내장 파일을 준비하므로 잠시 기다리세요.\r\n\r\n"
            "밸브를 클릭하면 초록색(열림), 다시 클릭하면 빨간색(닫힘)이 됩니다.\r\n"
            "손잡이 색상과 방향이 바뀌며 밸브 본체가 도면 이미지에 표시됩니다.\r\n"
            "공유한 PDF의 GC-1512A 원본 도면이 기본 화면에 포함되어 있습니다.\r\n"
            "원본 녹색 12개와 빨강 9개 손잡이의 초기 상태를 유지합니다.\r\n"
            "다른 도면은 이미지 열기로 적용하고 위치 편집에서 밸브를 맞추세요.\r\n"
            "프로젝트 저장으로 도면, 밸브 위치, 상태를 함께 보관할 수 있습니다.\r\n"
            "현재 기능은 화면에서 상태를 변경하는 시뮬레이션입니다.\r\n\r\n"
            "validation.json에는 실제 Windows GUI, CMD, EXE 실행 검증 결과가 있습니다.\r\n"
        )
        archive = output / ARCHIVE_NAME
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            bundle.write(executable, "ValveControl.exe")
            bundle.write(validation_file, "validation.json")
            bundle.writestr("README_WINDOWS.txt", instructions.encode("utf-8-sig"))
        with zipfile.ZipFile(archive) as bundle:
            if bundle.testzip() is not None or set(bundle.namelist()) != {"ValveControl.exe", "validation.json", "README_WINDOWS.txt"}:
                raise BuildFailure("ZIP integrity or expected file list verification failed")
            if hashlib.sha256(bundle.read("ValveControl.exe")).hexdigest() != file_details(executable)["sha256"]:
                raise BuildFailure("ZIP contains an executable differing from the tested executable")
        status["phases"][phase] = {"status": "passed", **file_details(archive)}
        status["archive"] = file_details(archive)
        status["status"] = "passed"
        returncode = 0
    except Exception as error:
        status["status"] = "failed"
        status["failed_phase"] = phase
        status["phases"][phase] = {"status": "failed", "reason": str(error)[:500]}
        print(f"FAILED [{phase}]: {error}", file=sys.stderr, flush=True)
        returncode = 1
    status["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(status_path, status)
    return returncode


def finalize_status(args) -> int:
    output = args.output_directory.resolve()
    path = output / "windows-build.json"
    status = json.loads(path.read_text(encoding="utf-8")) if path.exists() else base_status(args)
    status["workflow_steps"] = {"dependencies": args.dependency_outcome, "build": args.build_outcome}
    if status["status"] != "passed":
        status["status"] = "failed"
        if args.dependency_outcome != "success":
            status["failed_phase"] = "dependencies"
            status["phases"]["dependencies"] = {
                "status": "failed", "reason": "Pinned Python/Pillow/PyInstaller installation did not succeed",
            }
    status["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(path, status)
    print(json.dumps({"status": status["status"], "source_commit": status["source_commit"],
                      "failed_phase": status.get("failed_phase")}), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--source-sha", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--run-url", default="")
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--dependency-outcome", default="unknown")
    parser.add_argument("--build-outcome", default="unknown")
    args = parser.parse_args()
    return finalize_status(args) if args.status_only else build(args)


if __name__ == "__main__":
    raise SystemExit(main())
