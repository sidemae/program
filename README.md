# 밸브 모식 제어 1.1.1

공유한 [그림.pdf](그림.pdf)의 첫 번째 GC-1512A 도면을 기본으로 포함했습니다. **밸브 자체를 클릭하면 도면 속 손잡이가 90도 회전하고 색이 바뀝니다.** 녹색·배관과 나란함은 열림, 빨강·배관과 직각은 닫힘입니다.

## 다운로드

[Windows 실행 파일 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-windows-1.1.1.zip)

Windows 10/11 64비트에서 ZIP을 모두 압축 해제하고 **ValveControl.exe**를 더블 클릭하세요. Python 설치가 필요하지 않습니다. 원본 도면이 내장되어 표시됩니다.

[Python 소스 ZIP 다운로드](https://github.com/sidemae/program/raw/refs/heads/delivery/valve-control-1.0/valve-control-1.1.1.zip)

Python 3.11 이상을 설치한 뒤 소스 ZIP을 모두 압축 해제하고 `valve-control/run_windows.cmd`를 실행합니다. 자세한 방법은 [사용 설명서](valve-control/README.md)에 있습니다.

## 변경한 동작

- 도면 자체의 손잡이 색·방향을 변경하며 밸브 위의 원형 상태 버튼을 제거했습니다.
- 원본의 20개 밸브를 녹색 12개 열림·빨강 8개 닫힘 상태로 시작합니다. GAS N2의 두 빨간 손잡이는 같은 V08 밸브로 함께 움직이며, 별도 V21 중복 항목은 제거했습니다.
- 금속 밸브 몸체나 손잡이 끝을 클릭해 조작합니다. 정상 모드에서는 도면 이미지만 표시합니다.
- 원본 손잡이 그림을 픽셀 단위로 보존하고 실제 금속 연결축을 중심으로 회전합니다. 초기 화면은 원본 도면과 일치하며, 회전 후 이전 손잡이 잔상이나 추가 원형 표시가 없습니다.
- 사용자가 밸브 ID·설명·배관 방향을 수정할 수 있습니다. 중복 ID는 입력을 막고 위치·상태는 유지합니다.
- 배경·편집 위치·손잡이 형상·사용자 ID·설명·현재 상태를 `.vcp` 프로젝트에 함께 저장하고 복원합니다.

초기 화면과 클릭 전환 화면은 아래에서 확인할 수 있습니다.

[원본 초기 상태 화면](valve-control/artifacts/implementation_closed.png) · [개폐 전환 화면](valve-control/artifacts/implementation_open.png)

## 검증

Linux에서 실제 GUI 검사 55개를 통과했습니다. 원본 PDF 도면의 로딩, 실제 손잡이 색·방향 전환, 이미지 외곽 보존, 원본 상태 인식과 잔상 제거, 저장·복원 등을 확인했습니다. [GUI 검증 결과](valve-control/artifacts/validation.json)를 볼 수 있습니다.

Windows에서 GUI 검사 55개, CMD 실행 검사 8개, 독립 EXE 실행 검사 8개를 모두 통과했습니다. 원본 그림의 픽셀 일치, 실제 밸브 20개 클릭 좌표, ID·설명 편집과 중복 방지를 실행 파일에서도 확인했습니다. 게시된 ZIP을 다시 다운로드해 무결성과 검증된 EXE의 일치도 확인했습니다. [빌드 결과](windows-build.json), [Windows 실행 기록](https://github.com/sidemae/program/actions/runs/37720762108)을 볼 수 있습니다.

- Windows ZIP 크기: 21,443,689바이트 (약 21MB)
- SHA256: `b26d1535b7f91e70d9ae978745367edce933c9921805f379c8c882d2f6d1ee57`

새 도면의 자동 인식 위치는 편집으로 조정할 수 있습니다. 현재는 화면상의 시뮬레이션이며 실제 장비 통신·밸브 구동·유량 계산은 포함하지 않습니다.
