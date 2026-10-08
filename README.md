# Python 밸브 모식 제어 프로그램

이미지를 배경 레이어로 사용하고, 밸브를 클릭해 **초록색(열림) ↔ 빨간색(닫힘)**으로 상태를 전환하는 데스크톱 프로그램입니다.

## ZIP 다운로드

[valve-control-1.0.zip 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-1.0.zip)

직접 다운로드가 시작되지 않으면 [ZIP 파일 페이지](https://github.com/sidemae/program/blob/delivery/valve-control-1.0/valve-control-1.0.zip)에서 **Download raw file** 버튼을 누르세요. 비공개 저장소인 경우 접근 권한이 있는 GitHub 계정으로 로그인해야 합니다.

- 크기: 298,772바이트
- SHA256: `9e607a1a99419f9389ad4fb52fd6f90dddc449420947a149dd7365150d3de7cc`
- 포함: 단일 파일 Python 프로그램, 버전 고정 의존성, Windows/Linux 실행 도구, 사용 안내, GUI 검증 스크립트, 검증 결과와 실행 화면

## 실행

Python 3.11 이상을 설치하고 ZIP을 압축 해제한 뒤 `valve-control` 폴더의 **run_windows.cmd**를 실행하세요. 첫 실행 시 가상환경을 만들고 Pillow를 설치합니다.

직접 실행할 수도 있습니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe valve_control.py
```

이 명령은 ZIP의 `valve-control` 폴더에서 실행합니다. Linux와 macOS 실행 방법, 이미지 적용, 밸브 추가·삭제·속성 편집, 프로젝트 저장 방법은 [사용 설명서](valve-control/README.md)에 있습니다.

## 주요 기능

- 이미지 불러오기 및 창 크기에 따른 비율 유지
- 밸브 클릭·목록 더블클릭으로 열림/닫힘 전환
- 위치 편집, 밸브 추가·삭제, 이름·배관 방향 변경
- 배경 이미지·밸브 배치·현재 상태를 포함하는 `.vcp` 프로젝트 저장·복원
- 배치 JSON 및 현재 상태 JSON 내보내기
- 잘못된 파일 거부, 원자적 저장, 미저장 변경 보호

## 검증과 범위

Linux의 Python 3.13.5 / Tk 8.6.16 / Pillow 12.3.0에서 **실제 GUI 검증 40개를 통과**했습니다. [검증 결과](valve-control/artifacts/validation.json), [닫힘 화면](valve-control/artifacts/implementation_closed.png), [개폐 조작 화면](valve-control/artifacts/implementation_open.png)을 볼 수 있습니다.

처음 실행되는 배경은 독립적으로 그린 데모 도면이며, V01~V20은 임시 배치입니다. 채팅 첨부 원본의 파일 데이터가 머신에 제공되지 않아 원본 위의 위치 정합은 검증하지 않았습니다. **이미지 열기**로 보유한 도면을 적용한 뒤 위치 편집으로 맞추세요.

현재는 화면상의 상태 시뮬레이션이며 실제 장비 통신·밸브 구동·유량 계산은 포함하지 않습니다. Windows/macOS 실행 자체는 아직 검증하지 않았습니다.

작성일: 2026-10-08.
