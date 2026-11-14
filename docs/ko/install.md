# 설치와 실행

한국어 | [English](../install.md)

## 소스에서 실행

Python 3.11 이상을 사용합니다. 저장소 폴더에서 실행하세요.

```sh
python -m venv .venv
```

Windows 명령 프롬프트에서는 `.venv\Scripts\activate`,
Linux·macOS에서는 `source .venv/bin/activate`로 활성화한 뒤 실행합니다.

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

별도 실행 의존성이 없는 Core·CLI는 `python -m pip install .`로 설치합니다.
설치 후 `radixscope`, `radixscope-gui` 명령을 사용할 수 있습니다.

## Windows 실행 파일

Windows에서 64비트 Python 3.11 이상을 `python` 명령으로 사용할 수 있어야 합니다.

```powershell
.\build_windows.bat
```

BAT는 현재 Python 환경에 빌드 의존성을 설치하고
`dist/RadixScope/RadixScope.exe`를 만듭니다. 해당 폴더에서 실행하고
`_internal/`, `licenses/`를 함께 유지하세요. 빌드한 프로그램에는 Python과 Qt가 포함됩니다.
설치 프로그램이나 ZIP은 생성하지 않습니다.

## 설정과 업데이트

설정은 프로그램 폴더와 분리된 Qt의 사용자별 앱 데이터 디렉터리 아래
`Koreapanda4444/RadixScope/state.json`에 유지됩니다.
빌드한 프로그램 폴더를 교체하기 전에 앱을 종료하세요. 다른 PC로 옮길 때는 설정 파일을 보존하세요.

소스에서 실행하는 경우 앱을 종료한 뒤 업데이트합니다.

```sh
git pull --ff-only origin main
python -m pip install --upgrade ".[gui]"
```

## Linux 그래픽 라이브러리

Qt에는 시스템 그래픽 라이브러리가 필요합니다. Ubuntu·Debian에서는 다음과 같이 설치합니다.

```sh
sudo apt-get update
sudo apt-get install -y libegl1 libopengl0 libxkbcommon0
```

XCB 데스크톱에는 `libxcb-cursor0`과 배포판의 일반 X11 라이브러리가 추가로 필요할 수 있습니다.
GUI 의존성은 프로젝트의 버전 조건에 따라 설치하세요.

## 검증과 아이콘 리소스

소스 패키지 설치 후 `python scripts/check_numeric.py`로 Core·CLI를 확인합니다.
Qt 검증에는 `--desktop`, binary16·bfloat16 전체 패턴 확인에는 `--exhaustive`를 추가합니다.
Windows 빌드 후에는 다음 명령을 사용합니다.

```powershell
python scripts/check_numeric.py --desktop --exe dist/RadixScope/RadixScope.exe
```

x64 리소스, 패키징된 계산, 실제 창 아이콘과 정상 종료를 확인합니다.
`build/windows/`에 ICO, 일곱 크기의 PNG와 제품 메타데이터를 생성합니다.
`src/radixscope/assets/`의 두 SVG가 Qt와 EXE의 공통 아이콘 원본이며,
고정 Windows 앱 식별자로 실행 중인 창을 묶습니다.
폴더 교체 후 탐색기에 예전 아이콘이 남으면 새 EXE 리소스를 먼저 확인해
셸 캐시와 렌더링 문제를 구분할 수 있습니다.

데스크톱 검증 워크플로도 같은 BAT를 사용합니다. 워크플로 아티팩트에는 아이콘 검증
리소스를 보관하며, 프로그램 빌드 결과는 BAT가 생성하는 프로그램 폴더에 있습니다.
