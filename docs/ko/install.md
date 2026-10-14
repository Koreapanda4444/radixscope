# 설치

[한국어 README](../../README.ko.md) | [English](../install.md)

소스·휠 설치에는 Python 3.11 이상이 필요합니다. Windows에서는 `python` 대신 `py`를
사용할 수 있습니다. 아래 데스크톱 ZIP은 Python을 별도로 설치하지 않아도 됩니다.

## Windows 데스크톱 ZIP

성공한 [Quality 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)에서
`RadixScope-windows-x64` 산출물을 내려받으세요. 산출물 ZIP과 그 안의
`RadixScope-2.1.0-windows-x64.zip`을 풀고 `RadixScope/RadixScope.exe`를 실행합니다.
Python과 Qt가 포함되어 있어서 Python이나 pip를 별도로 설치할 필요가 없습니다.
`_internal` 폴더는 실행 파일 옆에 유지해야 하며, 업데이트는 새 폴더에 압축을 풀어서 합니다.
설정은 Python으로 설치한 앱과 같은 사용자별 앱 데이터 폴더에 저장합니다.

## 저장소에서 설치

```sh
git clone https://github.com/Koreapanda4444/radixscope.git
cd radixscope
python -m venv .venv
```

Windows 명령 프롬프트에서는 `.venv\Scripts\activate`, PowerShell에서는
`.venv\Scripts\Activate.ps1`, Linux에서는 `source .venv/bin/activate`로 가상 환경을
활성화합니다. 이후 다음 명령을 실행하세요.

```sh
python -m pip install --upgrade pip
python -m pip install ".[gui]"
python -m radixscope.gui
```

외부 의존성 없는 코어와 명령줄만 설치하려면 `python -m pip install .`을 사용합니다.
`gui` 추가 옵션은 PySide6와 Qt를 설치합니다. PySide6가 없으면 데스크톱 실행 명령이
필요한 추가 옵션을 안내합니다.

## 배포 패키지에서 설치

GitHub Actions에서 성공한 [Quality 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)을
열고 패키지 산출물을 내려받은 다음 ZIP을 풉니다. 휠 파일이 있는 폴더에서 실행하세요.

```sh
python -m pip install "radixscope-2.1.0-py3-none-any.whl[gui]"
radixscope-gui
```

명령줄만 필요하면 `[gui]`를 생략합니다. 배포 파일은 Python 패키지이므로 Python이
필요합니다. 독립 실행형 데스크톱 ZIP은 위에서 설명한 별도 산출물입니다.

## Linux 데스크톱 라이브러리

Qt는 화면 없는 환경에서 불러올 때도 시스템 그래픽 라이브러리가 필요합니다.
Ubuntu/Debian에서는 데스크톱 그래픽 라이브러리를 설치할 수 있습니다.

```sh
sudo apt-get update
sudo apt-get install -y libegl1 libopengl0
```

Qt의 XCB 플랫폼으로 데스크톱을 실행하는 환경에서는 `libxcb-cursor0`와 일반적인
X11 런타임 라이브러리도 필요할 수 있습니다. 화면 없는 실행에는
`QT_QPA_PLATFORM=offscreen`을 사용합니다. 이 설정에서는 데스크톱 창이 열리지 않습니다.

## 기존 저장소 업데이트

```sh
git pull --ff-only origin main
python -m pip install --upgrade ".[gui]"
python -m radixscope.gui
```

설정과 최근 입력은 Qt의 사용자별 앱 데이터 폴더에 있는
`Koreapanda4444/RadixScope/state.json`에 저장합니다.

사용 방법은 [데스크톱 안내](desktop.md)와 [명령줄 안내](cli.md)를 참고하세요.

## 데스크톱 ZIP 직접 빌드

Windows x64에서 Python 3.12로 실행합니다.

```sh
python -m pip install -e ".[desktop-build]"
python scripts/build_desktop.py
```

ZIP은 `dist/`에 생성합니다. 압축을 풀고 `RadixScope/RadixScope.exe`를 실행하세요.
