# 밸브 모식 제어 1.1.2

공유한 [그림.pdf](그림.pdf)의 GC-1512A 도면에서 **밸브 자체를 클릭해 녹색(열림)·빨강(닫힘)으로 전환**합니다. 수동 손잡이는 90도 회전하고, 자동·조절밸브와 조작 휠은 본래 형상을 유지하며 색이 바뀝니다.

## 다운로드

[Windows EXE 1.1.2 ZIP 다운로드 · 약 22MB](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-windows-1.1.2.zip)

Windows 10/11 64비트에서 ZIP을 모두 압축 해제하고 **ValveControl.exe**를 더블 클릭하세요. Python 설치가 필요하지 않습니다.

[Python 소스 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-1.1.2.zip)

Python 3.11 이상을 설치하고 ZIP을 모두 압축 해제한 뒤 `valve-control/run_windows.cmd`를 실행하세요. 자세한 방법은 [사용 설명서](valve-control/README.md)에 있습니다.

## 수정한 동작

- 수동 밸브 20개, 자동·조절밸브 3개, 압축기 조작 휠 6개를 등록해 총 29개를 조작합니다.
- V08은 한 개의 손잡이로 표시합니다. 기존 위쪽 중복 손잡이와 연결 팔을 제거했습니다.
- 움직이는 손잡이에서 흰 배경과 고정된 금속부를 분리했습니다. 드레인 뒤의 두 지지대를 복원하고, 다른 밸브 몸통·배관은 회전한 손잡이 앞에 유지합니다.
- 원래 파란 구동부와 휠은 초기 닫힘·빨강으로 설정합니다. 초기 열림 14개·닫힘 15개이며 화면상의 시뮬레이션 상태입니다.
- 사용자가 밸브 ID·설명·배관 방향을 수정할 수 있습니다. 중복 ID는 거부하며 위치·상태를 유지합니다.
- 배경·위치·밸브 형상·사용자 ID·설명·현재 상태를 `.vcp` 프로젝트로 저장하고 복원합니다.

1.1.1 이하에서 저장한 프로젝트에는 당시 그림과 등록 목록이 남아 있습니다. 새 프로그램의 **기본 도면**에서 수정된 29개 제어 대상을 여세요. 먼저 기존 프로젝트를 별도 파일에 저장하면 이전 편집을 보관할 수 있습니다.

[초기 화면](valve-control/artifacts/implementation_closed.png) · [개폐 전환 화면](valve-control/artifacts/implementation_open.png)

## 검증

Linux에서 실제 GUI 검사 60개를 통과했습니다. 29개 제어 대상의 실제 몸통 좌표를 최소·확대 창 크기에서 클릭하고, 자동밸브 구동부 직접 클릭, 단일 V08, 인접한 금속부·지지대 보존, 전체 밸브의 반복 조작, 사용자 ID·설명과 프로젝트 복원을 확인했습니다. [GUI 검증 결과](valve-control/artifacts/validation.json)를 볼 수 있습니다.

Windows에서도 GUI 검사 60개, CMD 실행 검사 11개, 소스 폴더 없이 실행하는 독립 EXE 검사 11개를 통과했습니다. 한글·공백 경로에서도 실행하고, 29개 실제 좌표와 자동·조절밸브 색 전환, 단일 V08, 반복 조작 후 이미지 보존과 ID·설명 편집을 확인했습니다. 게시된 ZIP을 다시 다운로드해 무결성과 검증된 EXE의 일치도 확인했습니다. [빌드 보고서](windows-build.json), [Windows 실행 기록](https://github.com/sidemae/program/actions/runs/37739000164)을 볼 수 있습니다.

- Windows ZIP: 22,174,510바이트
- SHA256: `60ce8aaf0c7a49a557a6a4a3147a0e8c40d577fb1647e674cdfabe81f5d7eac0`

현재 기능은 화면상의 시뮬레이션입니다. 실제 장비 통신·밸브 구동·유량 계산은 포함하지 않습니다.
