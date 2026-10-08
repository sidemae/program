# 밸브 모식 제어 1.1.1

공유한 `그림.pdf`의 첫 번째 GC-1512A 도면을 기본 화면으로 포함했습니다. **밸브 몸체 또는 손잡이를 클릭하면 도면 속 손잡이 자체의 색과 방향이 바뀝니다.** 녹색·배관과 나란함은 열림, 빨강·배관과 직각은 닫힘입니다.

## Windows 실행

저장소의 [Windows 실행 파일 ZIP](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-windows-1.1.1.zip)을 모두 압축 해제하고 `ValveControl.exe`를 더블 클릭하세요. Python 설치가 필요하지 않습니다. 원본 GC-1512A 도면이 내장되어 처음부터 표시됩니다.

Python 소스로 실행하려면 Python 3.11 이상을 설치하고 이 폴더의 `run_windows.cmd`를 실행하세요. 처음에는 가상환경과 Pillow를 설치하므로 PyPI 접속이 필요합니다. 실행 도구는 ASCII·CRLF 형식입니다. 직접 실행할 수도 있습니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe valve_control.py
```

## 조작

1. 도면의 금속 밸브 몸체나 손잡이를 클릭하면 손잡이가 90도 회전하고 녹색/빨강으로 전환합니다. 우측 상태 목록도 함께 바뀝니다.
2. 처음에는 원본의 20개 밸브를 열림 12개·닫힘 8개 상태로 적용합니다. 원본의 GAS N2 빨간 손잡이 두 개는 같은 V08 밸브로 연동합니다. 별도 V21 중복 항목은 제거했습니다. V01~V20은 프로그램의 편집용 번호입니다.
3. 다른 도면은 **이미지 열기**로 PNG/JPG/BMP/WebP를 선택합니다. 가늘고 긴 빨강·녹색 손잡이를 인식하여 원본의 색을 초기 상태로 읽습니다. 손잡이의 원본 그림을 분리해 보존하고 회전·색 전환에 사용합니다. 큰 녹색 장비 몸체와 둥근 핸드휠은 손잡이 인식에서 제외합니다. 원본 이미지 파일은 수정하지 않습니다.
4. **위치 편집**에서 위치를 맞출 수 있습니다. 밸브를 선택하고 오른쪽의 **밸브 ID**, **설명 / 위치 이름**, 배관 방향을 수정한 뒤 **변경 적용**을 누르세요. 중복 ID는 거부하며 변경한 ID·설명은 프로젝트에 저장됩니다. 새 도면의 자동 인식 위치는 조정이 필요할 수 있습니다. 편집 모드에서는 상태가 바뀌지 않습니다. 필요하면 **밸브 추가**, **삭제**를 사용하세요. ID와 선택 테두리는 편집 모드에서만 표시됩니다. **기본 도면** 버튼으로 내장 도면의 정확한 위치와 초기 상태를 다시 열 수 있습니다.
5. **저장**으로 `.vcp` 프로젝트를 만듭니다. 배경·밸브 배치·손잡이 크기/축 위치·현재 상태를 하나의 파일에 저장하므로 다른 PC에서도 원본 이미지 없이 복원할 수 있습니다.

목록 더블 클릭, 스페이스, 우측 개폐 전환 버튼으로도 조작합니다. 창 크기를 바꾸면 이미지 비율과 클릭 위치가 함께 유지됩니다. 미저장 상태에서 닫거나 도면을 바꾸면 저장·버리기·취소를 선택합니다.

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
- `valve_render.py`: 그림 속 손잡이 인식·정리·색상/방향 렌더링과 클릭 영역.
- `assets/GC-1512A.png`: PDF의 제목·테두리까지 포함해 렌더링한 원본 도면.
- `assets/GC-1512A.vcp`: 원본 손잡이를 분리하고 기본 위치·초기 상태를 설정한 프로젝트.
- `assets/source.json`: PDF 출처와 추출 방법.
- `requirements.txt`, `run_windows.cmd`, `run.sh`: 의존성과 실행 도구.
- `verify_gui.py`, `artifacts/`: 실제 GUI 검증과 화면.
- `build_windows.py`: Windows에서 GUI·CMD·EXE 검증 후 ZIP 생성.

Linux에서 실제 GUI 검사 55개를 통과했습니다. 원본 PDF 도면, 이미지 안의 손잡이 회전/색 전환, 주변 이미지 보존, 손잡이 끝 클릭, 원본 상태 인식, 잔상 제거, 저장·복원과 오류 처리를 확인했습니다. Windows 빌드 결과는 저장소의 `windows-build.json`과 EXE ZIP의 `validation.json`에 기록됩니다. 검증된 실행 파일만 게시합니다.

클라우드에서 재검증:

```bash
cd /workspace/program/valve-control
XDG_CACHE_HOME=/workspace/.cloud-setup/cache /workspace/.cloud-setup/gui-venv/bin/python verify_gui.py
```

현재 기능은 화면상의 상태 시뮬레이션입니다. 실제 PLC·장비 통신, 밸브 구동, 유량 계산은 포함하지 않습니다.
