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

Windows에서 x64 Python 3.11 이상을 `python` 명령으로 사용할 수 있어야 합니다.

```powershell
.\build_windows.bat
```

BAT는 호환되는 빌드 의존성을 재사용하며, 필요한 경우에만 설치한 뒤 프로젝트 루트에
`RadixScope.exe`를 만듭니다. `_internal/`을 EXE 옆에 유지하세요. 빌드한 프로그램에는 Python과 Qt가 포함됩니다.
설치 프로그램이나 ZIP은 생성하지 않습니다. 필요한 의존성이 이미 설치돼 있으면
로컬 고지 자료를 사용하므로 패키징에 네트워크가 필요하지 않습니다.
Windows 빌드에는 검토된 PySide6·Qt 6.11.3을 사용합니다.
`packaging/notices/sources.json`에 원문 URL·수집일·검토한 런타임 버전·SHA-256을 기록합니다.
버전이나 해시가 다르면 산출물을 교체하기 전에 중단하므로, 런타임을 바꿀 때 고지와 출처도
함께 검토해야 합니다. Python 설치에 포함된 해당 버전의 `LICENSE.txt`도 보존합니다.

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

## Windows 아이콘 리소스

`build/windows/`에 ICO, 일곱 크기의 PNG와 제품 메타데이터를 생성합니다.
`src/radixscope/assets/`의 두 SVG가 Qt와 EXE의 공통 아이콘 원본이며,
고정 Windows 앱 식별자로 실행 중인 창을 묶습니다.
폴더 교체 후 탐색기에 예전 아이콘이 남으면 새 EXE 리소스를 먼저 확인해
셸 캐시와 렌더링 문제를 구분할 수 있습니다.

EXE는 `build_windows.bat`가 있는 루트에, 런타임은 `_internal/`, 고지는
`_internal/licenses/`에 생성합니다. PyInstaller는 수집 폴더를 정리하므로 소스를
보호하기 위해 `build/windows/stage/`에서 중간 수집한 뒤 해시 목록으로 출력 파일만 배치합니다.
사용자가 수정한 파일과 출처를 확인할 수 없는 파일은 덮어쓰지 않습니다.
제품을 확인한 이전 `dist` EXE는 `.exe.previous-build`로 이름을 바꾸며, 확인할 수 없는
산출물은 직접 이동한 뒤 빌드해야 합니다. 다른 사용자 파일은 보존합니다.
`_internal/licenses/NOTICE.html`에서 라이선스 원문, 구성요소와 동일 버전 소스 위치를 확인합니다.
LGPL 라이브러리는 `_internal/`에서 교체할 수 있으며 재배포 시 고지와 해당 소스에 대한
동등한 접근을 함께 유지해야 합니다.
