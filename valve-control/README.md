# 밸브 모식 제어 1.0.1

승인된 컨셉에 따라 Python으로 구현한 독립 실행 프로그램입니다. 이미지를 배경 레이어로 표시하고, 밸브를 클릭하면 초록색(열림), 다시 클릭하면 빨간색(닫힘)으로 전환합니다.

## Windows 실행

Windows 실행 파일 ZIP은 저장소의 [다운로드 안내](https://github.com/sidemae/program/blob/delivery/valve-control-1.0/README.md)에서 받습니다. 모두 압축 해제한 뒤 `ValveControl.exe`를 더블 클릭하면 됩니다. Python 설치가 필요하지 않습니다.

다음은 Python 소스 ZIP 실행 방법입니다.

Python 3.11 이상을 설치한 뒤 ZIP을 압축 해제하고 `run_windows.cmd`를 실행합니다. 이 스크립트는 이 폴더에 `.venv`를 만들고 Pillow를 설치한 뒤 프로그램을 시작합니다. 최초 설치에는 PyPI 접속이 필요합니다.

명령으로 실행하려면 이 폴더에서 다음을 입력합니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe valve_control.py
```

Python의 Tkinter가 필요하며 공식 Windows Python 설치본에는 포함됩니다. 1.0.1에서는 CMD 실행 도구를 ASCII·CRLF 형식으로 수정했습니다. Windows용 빌드와 CMD·EXE 실행 검증 결과는 저장소의 `windows-build.json`에 기록됩니다. 검증에 통과한 ZIP만 게시합니다.

## Linux / macOS 실행

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python valve_control.py
```

Linux에서는 배포판의 Tkinter 패키지와 한글 글꼴이 필요합니다. 이 클라우드에서 디스플레이가 있으면 `./run.sh`를 사용합니다. 디스플레이 없는 클라우드에서는 아래의 검증 명령을 사용합니다. macOS 실행 자체는 아직 검증하지 않았습니다.

## 사용 순서

1. **이미지 열기**로 도면 PNG/JPG/BMP/WebP를 선택합니다. 원본 파일은 수정하지 않습니다. 투명 PNG는 흰색 바탕 위에 표시합니다.
2. **위치 편집**을 켜고 기존 밸브를 드래그하거나, 선택한 밸브가 놓일 배경 위치를 클릭합니다. 편집 모드에서는 개폐 상태가 바뀌지 않습니다.
3. **밸브 추가**를 누르고 그림의 위치를 클릭합니다. 목록에서 선택해 이름과 배관 방향을 설정한 뒤 **이름·방향 적용**을 누릅니다. `horizontal`은 가로 배관, `vertical`은 세로 배관입니다. 삭제도 목록에서 선택 후 실행합니다.
4. **위치 편집**을 끄고 밸브를 클릭해 상태를 전환합니다. 목록 더블클릭, 선택 후 스페이스 또는 **개폐 전환** 버튼으로도 조작할 수 있습니다.
5. **저장**으로 `.vcp` 프로젝트를 만듭니다. **배경 이미지·밸브 배치·이름·배관 방향·현재 열림/닫힘 상태**가 하나의 파일에 포함됩니다. 다른 폴더나 PC로 옮겨도 원본 이미지 파일 없이 복원할 수 있습니다.

상단에는 열림·닫힘 개수가, 오른쪽에는 상태 목록과 조작 이력이 표시됩니다. 창 크기를 바꾸면 이미지 비율과 밸브 좌표가 함께 유지됩니다. 편집한 프로젝트를 저장하지 않고 닫거나 교체하면 저장·버리기·취소를 선택할 수 있습니다.

## 배치와 상태 파일

파일 메뉴의 **배치 JSON 저장**은 이름·좌표·방향을 저장하고 초기 상태를 모두 닫힘으로 둡니다. **현재 상태 JSON 내보내기**는 당시의 모의 상태를 별도 파일로 기록합니다. 현재 상태를 다시 복원하려면 `.vcp` 프로젝트를 사용하세요.

기존 초안의 `layout.json`은 불러올 수 있습니다. 지원하지 않는 버전, 좌표계, 중복 ID 또는 잘못된 좌표는 거부하며 기존 프로젝트를 유지합니다. 프로젝트와 JSON은 임시 파일에 완전히 기록한 뒤 교체하므로 저장 실패 시 기존 파일을 보호합니다.

```bash
python valve_control.py --image diagram.png --layout layout.json
python valve_control.py --project my_diagram.vcp
```

## 기본 도면과 범위

처음 실행하면 독립적으로 그린 데모 배관과 주요 밸브 20개의 임시 위치를 표시합니다. 채팅 첨부의 원본 이미지 데이터는 머신에 제공되지 않아, 원본 이미지 위의 정합은 검증하지 않았습니다. PC에서 보유한 원본 이미지를 열어 위치 편집으로 맞출 수 있습니다. V01~V20은 임시 번호이며 확정된 장비 태그가 아닙니다.

이 프로그램은 상태 시뮬레이션입니다. PLC 통신, 실제 밸브 개폐 명령, 유량 계산은 포함하지 않습니다. 프로젝트 저장은 모의 상태의 복원이며 장비에 명령을 보내지 않습니다. 종료 후 조작 이력은 유지되지 않으며, 필요한 당시 상태는 프로젝트 또는 상태 JSON으로 보관하세요.

## 검증

Python 3.13.5 / Tk 8.6.16 / Pillow 12.3.0의 Linux 환경에서 실제 GUI를 검증했습니다. 정확한 검증 개수와 항목은 `artifacts/validation.json`에 있습니다. 화면은 `artifacts/implementation_closed.png`, `artifacts/implementation_open.png`입니다.

이 클라우드에서 재검증하려면 다음을 실행합니다.

```bash
cd /workspace/valve-control
XDG_CACHE_HOME=/workspace/.cloud-setup/cache /workspace/.cloud-setup/gui-venv/bin/python verify_gui.py
```

검증 스크립트는 필요한 경우 Xvfb를 자동 시작하고 실제 Tk 클릭·드래그·목록 조작·파일 저장을 수행한 뒤 자신이 시작한 프로세스를 종료합니다. Linux의 다른 머신에는 `Xvfb`가 설치되어 있어야 합니다.

## 패키지

- `valve_control.py`: 단일 파일 프로그램. 다른 소스 모듈 없이 실행됩니다.
- `requirements.txt`: Pillow 버전 고정.
- `run_windows.cmd`, `run.sh`: 실행 도구.
- `verify_gui.py`: 실제 GUI 검증.
- `build_windows.py`: Windows에서 CMD·EXE 검증 후 실행 파일 ZIP 생성. 저장소의 GitHub Actions에서 실행합니다.
- `artifacts/`: 검증 결과와 실행 화면.

작성일: 2026-10-08. 기존 `campus-mod` 프로젝트는 수정하지 않았습니다.
