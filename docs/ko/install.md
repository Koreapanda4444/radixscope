# 설치와 패키징

한국어 | [English](../install.md)

## Windows x64

성공한 [Quality 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)에서
`RadixScope-windows-x64`를 내려받고 Actions 산출물의 압축부터 풀어 주세요.

| 패키지 | 사용 방법 |
| --- | --- |
| `RadixScope-*-windows-x64-setup.exe` | 현재 사용자용으로 설치하고 시작 메뉴 바로가기와 제거 프로그램 제공 |
| `RadixScope-*-windows-x64.zip` | 압축을 풀고 `RadixScope/RadixScope.exe` 실행 |

두 형태 모두 Python 런타임, Qt, 아이콘, 한국어·영어 리소스, 문서와 제삼자 라이선스
고지를 포함합니다. 압축형은 EXE만 옮기지 말고 폴더 전체를 유지하세요.
기본 사용자 설치에는 관리자 권한이 필요하지 않습니다. 바탕화면 바로가기는 설치 중
선택할 수 있습니다. Windows의 설치된 앱 목록이나 `unins000.exe`로 제거합니다.

설정은 Qt의 사용자별 앱 데이터 디렉터리 아래
`Koreapanda4444/RadixScope/state.json`에 별도로 보관합니다. 제거 시 이 사용자 데이터는
지우지 않습니다. 압축형 업데이트는 앱을 닫고 새 폴더에 푸세요.
설치형 업데이트는 앱을 닫은 뒤 같은 설치 경로에 설치 파일을 실행합니다.

## Python 설치

소스와 휠 배포본에는 Python 3.11 이상이 필요합니다.

```sh
git clone https://github.com/Koreapanda4444/radixscope.git
cd radixscope
python -m venv .venv
```

Windows 명령 프롬프트에서는 `.venv\Scripts\activate`,
Linux에서는 `source .venv/bin/activate`로 가상환경을 활성화한 뒤 실행하세요.

```sh
python -m pip install --upgrade pip
python -m pip install ".[gui]"
python -m radixscope.gui
```

Core·CLI만 필요하면 `python -m pip install .`로 설치합니다.
내려받은 휠은 실제 파일명을 pip에 전달하고, GUI 의존성도 필요하면 따옴표 안의 파일명
뒤에 `[gui]`를 붙이세요. 휠·소스 압축 파일은 Actions의
`packages-<os>-py<python>` 산출물에 있습니다. 독립 실행 Windows 패키지와 달리 Python이 필요합니다.

```sh
git pull --ff-only origin main
python -m pip install --upgrade ".[gui]"
radixscope-gui
```

GUI 의존성에서는 [싱글턴 참조 카운트 오류](https://qt-project.atlassian.net/browse/PYSIDE-3474)가
있는 PySide6 6.12.0을 제외합니다. 프로젝트의 의존성 조건에 따라 설치하세요.

## Linux 그래픽 라이브러리

Qt는 화면 없이 실행할 때도 시스템 그래픽 라이브러리가 필요합니다.
Ubuntu·Debian에서는 다음과 같이 설치합니다.

```sh
sudo apt-get update
sudo apt-get install -y libegl1 libopengl0 libxkbcommon0
```

XCB를 사용하는 데스크톱 환경에는 `libxcb-cursor0`과 배포판의 일반 X11 라이브러리가
추가로 필요할 수 있습니다. `QT_QPA_PLATFORM=offscreen`은 창을 표시하지 않고 통합 검증을 실행합니다.

빌드와 검증은 [개발 안내](development.md)를 참고하세요.
