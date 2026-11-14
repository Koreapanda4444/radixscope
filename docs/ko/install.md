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
