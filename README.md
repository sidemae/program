# Python 밸브 모식 제어 프로그램

이미지를 배경으로 표시하고 밸브를 클릭해 **초록색(열림) ↔ 빨간색(닫힘)**으로 전환하는 데스크톱 프로그램입니다.

## Windows 실행 파일

[Windows 실행 파일 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-windows-1.0.1.zip)

Windows 10/11 64비트에서 ZIP을 모두 압축 해제하고 **ValveControl.exe**를 더블 클릭하세요. Python 설치나 CMD 실행이 필요하지 않습니다. 최초 시작 시 내장 파일을 준비하므로 잠시 기다리세요.

Windows 빌드에서 실제 GUI 40개 검사, 수정한 CMD 실행 검사, 한글·공백 경로의 EXE 실행 검사와 ZIP 무결성을 확인합니다. 검증에 통과한 실행 파일만 게시하며 [빌드 결과](windows-build.json)에 상태·검증 항목·SHA256·빌드 주소를 기록합니다. 빌드 진행 상태는 [GitHub Actions](https://github.com/sidemae/program/actions)에서 볼 수 있습니다.

## Python 소스

[수정한 Python 소스 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-1.0.1.zip)

Python 3.11 이상을 설치하고 ZIP을 모두 압축 해제한 뒤 `valve-control` 폴더의 **run_windows.cmd**를 실행하세요. 첫 실행 시 가상환경을 만들고 Pillow를 설치합니다. 1.0.1에서는 Windows CMD의 인코딩·줄바꿈 문제를 줄이도록 실행 도구를 ASCII·CRLF 형식으로 수정했습니다.

직접 실행하려면 해당 폴더에서 다음을 입력합니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe valve_control.py
```

기존 `valve-control-1.0.zip` 다운로드 주소에도 수정한 소스 ZIP을 제공합니다. Linux/macOS 실행과 자세한 조작 방법은 [사용 설명서](valve-control/README.md)에 있습니다.

## 주요 기능

- 이미지 불러오기 및 창 크기에 따른 비율 유지
- 밸브 클릭·목록 더블 클릭으로 개폐 상태 전환
- 위치 편집, 밸브 추가·삭제, 이름·배관 방향 변경
- 배경 이미지·밸브 배치·현재 상태를 포함하는 `.vcp` 프로젝트 저장·복원
- 배치 JSON 및 현재 상태 JSON 내보내기
- 잘못된 파일 거부, 원자적 저장, 미저장 변경 보호

## 검증과 범위

Linux의 Python 3.13.5 / Tk 8.6.16 / Pillow 12.3.0에서 실제 GUI 검증 40개를 통과했습니다. [검증 결과](valve-control/artifacts/validation.json), [닫힘 화면](valve-control/artifacts/implementation_closed.png), [개폐 조작 화면](valve-control/artifacts/implementation_open.png)을 볼 수 있습니다. Windows 결과는 위의 빌드 보고서에서 별도로 확인합니다. macOS 실행은 검증하지 않았습니다.

처음 실행되는 배경은 독립적으로 그린 데모 도면이며 V01~V20은 임시 배치입니다. 채팅 첨부 원본의 파일 데이터가 머신에 제공되지 않아 원본 위의 위치 정합은 검증하지 않았습니다. **이미지 열기**로 보유한 도면을 적용한 뒤 위치 편집으로 맞추세요.

현재는 화면상의 상태 시뮬레이션이며 실제 장비 통신·밸브 구동·유량 계산은 포함하지 않습니다.

작성일: 2026-10-08.
