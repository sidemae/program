# 밸브 모식 제어 1.1.2

공유한 `그림.pdf`의 첫 번째 GC-1512A 도면을 기본 화면으로 포함했습니다. **밸브 몸체 또는 손잡이를 클릭하면 밸브 자체가 녹색(열림)·빨강(닫힘)으로 바뀝니다.** 수동 레버는 90도 회전하고, 자동·조절밸브와 조작 휠은 본래 형상을 유지합니다.

## Windows 실행

저장소의 [Windows 실행 파일 ZIP](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-windows-1.1.2.zip)을 모두 압축 해제하고 `ValveControl.exe`를 더블 클릭하세요. Python 설치가 필요하지 않습니다. GC-1512A 도면이 내장되어 처음부터 표시됩니다.

Python 소스로 실행하려면 Python 3.11 이상을 설치하고 이 폴더의 `run_windows.cmd`를 실행하세요. 처음에는 가상환경과 Pillow를 설치하므로 PyPI 접속이 필요합니다. 실행 도구는 ASCII·CRLF 형식입니다. 직접 실행할 수도 있습니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe valve_control.py
```

## 조작

1. 도면의 금속 밸브 몸체나 손잡이를 클릭하면 상태가 바뀝니다. 수동 레버는 배관과 나란한 녹색이 열림, 배관과 직각인 빨강이 닫힘입니다. 자동·조절밸브는 구동부 자체의 색이 바뀌고, 조작 휠도 자체 색이 바뀝니다. 우측 상태 목록도 함께 바뀝니다.
2. 기본 도면에는 수동 밸브 20개(V01~V20), 조절밸브 1개(CV01), 자동밸브 2개(AV01~AV02), 압축기 조작 휠 6개(HV01~HV06)를 등록했습니다. 총 29개, 초기 열림 14개·닫힘 15개입니다. V08은 한 개의 손잡이만 사용하며 위쪽 중복 손잡이와 연결 팔을 제거했습니다. 파란색이던 자동밸브와 휠은 초기 닫힘·빨강으로 설정합니다. 프로그램 ID와 초기 상태는 편집할 수 있는 시뮬레이션 설정입니다.
3. 다른 도면은 **이미지 열기**로 PNG/JPG/BMP/WebP를 선택합니다. 가늘고 긴 빨강·녹색 손잡이를 인식하여 원본의 색을 초기 상태로 읽습니다. 다른 도면의 자동밸브·휠 위치는 자동으로 추정하지 않습니다. 내장 원본 PNG를 다시 열면 검토한 29개 등록과 V08 단일 손잡이를 적용합니다. 원본 이미지 파일은 수정하지 않습니다.
4. **위치 편집**에서 위치를 맞출 수 있습니다. 밸브를 선택하고 오른쪽의 **밸브 ID**, **설명 / 위치 이름**, 배관 방향을 수정한 뒤 **변경 적용**을 누르세요. 중복 ID는 거부하며 변경한 ID·설명은 프로젝트에 저장됩니다. 새 도면의 자동 인식 위치는 조정이 필요할 수 있습니다. 편집 모드에서는 상태가 바뀌지 않습니다. 필요하면 **밸브 추가**, **삭제**를 사용하세요. ID와 선택 테두리는 편집 모드에서만 표시됩니다. **기본 도면** 버튼으로 내장 도면의 정확한 위치와 초기 상태를 다시 열 수 있습니다.
5. **저장**으로 `.vcp` 프로젝트를 만듭니다. 배경·밸브 배치·손잡이 크기/축 위치·현재 상태를 하나의 파일에 저장하므로 다른 PC에서도 원본 이미지 없이 복원할 수 있습니다.

목록 더블 클릭, 스페이스, 우측 개폐 전환 버튼으로도 조작합니다. 창 크기를 바꾸면 이미지 비율과 클릭 위치가 함께 유지됩니다. 미저장 상태에서 닫거나 도면을 바꾸면 저장·버리기·취소를 선택합니다.

1.1.1 이하에서 저장한 프로젝트에는 당시 손잡이 이미지와 등록 목록이 남아 있습니다. 수정된 기본 화면은 새 프로그램의 **기본 도면**에서 여세요. 기존 프로젝트를 먼저 별도 파일로 저장하면 이전 편집을 보관할 수 있습니다.

## 파일

**배치 JSON 저장**은 초기 상태를 모두 닫힘으로 저장합니다. 현재 상태를 복원하려면 `.vcp`를 사용하세요. **현재 상태 JSON 내보내기**로 당시 상태만 기록할 수도 있습니다. 기존 배치 형식은 불러올 수 있습니다. 잘못된 파일은 기존 작업을 유지하며 거부하고, 저장 중 실패하면 기존 파일을 보호합니다.

```bash
python valve_control.py --image diagram.png --layout layout.json
python valve_control.py --project my_diagram.vcp
```

## Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python valve_control.py
```

Linux에서는 Tkinter와 한글 글꼴이 필요합니다. macOS 실행은 검증하지 않았습니다.

## 구성과 검증

- `valve_control.py`: Tkinter 프로그램, 편집과 프로젝트 관리.
- `valve_render.py`: 움직이는 손잡이와 고정 배관·지지대 분리, 색상/방향 렌더링과 클릭 영역.
- `assets/GC-1512A.png`: PDF의 제목·테두리까지 포함해 렌더링한 원본 도면.
- `assets/GC-1512A.vcp`: 검토한 29개 제어 대상과 V08 단일 손잡이를 설정한 프로젝트.
- `assets/GC-1512A.initial.png`: V08 중복 제거와 파란 구동부의 상태 색을 적용한 초기 화면.
- `assets/registration.json`, `prepare_reference.py`: 검토한 실제 픽셀 위치와 기본 프로젝트 재생성 도구.
- `assets/source.json`: PDF 출처와 추출 방법.
- `requirements.txt`, `run_windows.cmd`, `run.sh`: 의존성과 실행 도구.
- `verify_gui.py`, `artifacts/`: 실제 GUI 검증과 화면.
- `build_windows.py`: Windows에서 GUI·CMD·EXE 검증 후 ZIP 생성.

Linux에서 실제 GUI 검사 60개를 통과했습니다. 29개 제어 대상의 실제 좌표, 자동·조절밸브와 휠의 색 전환, V08 단일 손잡이, 고정 금속부 보존, 반복 조작과 저장·복원을 확인했습니다. 실행 결과는 `artifacts/validation.json`에 기록됩니다. Windows 빌드 결과는 저장소의 `windows-build.json`과 EXE ZIP의 `validation.json`에 기록됩니다. 검증된 실행 파일만 게시합니다.

클라우드에서 재검증:

```bash
cd /workspace/program/valve-control
XDG_CACHE_HOME=/workspace/.cloud-setup/cache /workspace/.cloud-setup/gui-venv/bin/python verify_gui.py
```

현재 기능은 화면상의 상태 시뮬레이션입니다. 실제 PLC·장비 통신, 밸브 구동, 유량 계산은 포함하지 않습니다.
