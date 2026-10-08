# 밸브 모식 제어 1.1.0

공유한 [그림.pdf](그림.pdf)의 첫 번째 GC-1512A 도면을 기본으로 포함했습니다. **밸브 자체를 클릭하면 도면 속 손잡이가 90도 회전하고 색이 바뀝니다.** 녹색·배관과 나란함은 열림, 빨강·배관과 직각은 닫힘입니다.

## 다운로드

[Windows 실행 파일 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-windows-1.1.0.zip)

Windows 10/11 64비트에서 ZIP을 모두 압축 해제하고 **ValveControl.exe**를 더블 클릭하세요. Python 설치가 필요하지 않습니다. 원본 도면이 내장되어 표시됩니다.

[Python 소스 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-1.1.0.zip)

Python 3.11 이상을 설치한 뒤 소스 ZIP을 모두 압축 해제하고 `valve-control/run_windows.cmd`를 실행합니다. 자세한 방법은 [사용 설명서](valve-control/README.md)에 있습니다.

## 변경한 동작

- 도면 자체의 손잡이 색·방향을 변경하며 밸브 위의 원형 상태 버튼을 제거했습니다.
- 원본의 21개 손잡이를 녹색 12개 열림·빨강 9개 닫힘 상태로 시작합니다. GAS N2 보조 손잡이도 포함합니다.
- 금속 밸브 몸체나 손잡이 끝을 클릭해 조작합니다. 정상 모드에서는 도면 이미지만 표시합니다.
- 새 도면의 빨강·녹색 손잡이를 인식해 초기 상태를 읽고 기존 손잡이를 교체하므로 회전 후에도 이전 손잡이 색이 남지 않습니다.
- 배경·편집 위치·손잡이 형상·현재 상태를 `.vcp` 프로젝트에 함께 저장하고 복원합니다.

초기 화면과 클릭 전환 화면은 아래에서 확인할 수 있습니다.

[원본 초기 상태 화면](valve-control/artifacts/implementation_closed.png) · [개폐 전환 화면](valve-control/artifacts/implementation_open.png)

## 검증

Linux에서 실제 GUI 검사 50개를 통과했습니다. 원본 PDF 도면의 로딩, 실제 손잡이 색·방향 전환, 이미지 외곽 보존, 원본 상태 인식과 잔상 제거, 저장·복원 등을 확인했습니다. [GUI 검증 결과](valve-control/artifacts/validation.json)를 볼 수 있습니다.

Windows에서 GUI·CMD·독립 EXE를 검증하고 ZIP 무결성까지 확인한 실행 파일을 게시합니다. 최신 [빌드 결과](windows-build.json)에 버전·상태·SHA256·실행 기록 주소를 기록합니다. [Actions](https://github.com/sidemae/program/actions)에서 빌드 진행 상태를 볼 수 있습니다.

새 도면의 자동 인식 위치는 편집으로 조정할 수 있습니다. 현재는 화면상의 시뮬레이션이며 실제 장비 통신·밸브 구동·유량 계산은 포함하지 않습니다.
