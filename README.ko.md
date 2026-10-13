# RadixScope

한국어 | [English](README.md)

RadixScope 2.1.0은 정확한 수를 2~36진법 사이에서 변환하고, 고정 비트 정수와
IEEE 754 부동소수점의 비트 표현을 확인하는 도구입니다. 명령줄 인터페이스와
PySide6 데스크톱 앱을 제공합니다.

## 설치와 실행

Windows x64에서는 성공한 [Quality 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)의
`RadixScope-windows-x64` 산출물을 내려받으면 됩니다. 산출물 ZIP을 풀고, 안에 있는
`RadixScope-2.1.0-windows-x64.zip`도 푼 다음 `RadixScope/RadixScope.exe`를 실행하세요.
`_internal`을 포함한 폴더 전체를 함께 유지해야 합니다. Python과 Qt가 포함되어 있습니다.

소스나 휠을 설치할 때는 Python 3.11 이상이 필요합니다. 저장소를 내려받은 폴더에서 실행하세요.

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

명령줄과 Python API만 사용할 때는 `python -m pip install .`로 설치합니다.
설치 후 `radixscope`, `radixscope-gui` 명령을 사용할 수 있습니다.
Windows에서는 위 명령의 `python` 대신 `py`를 사용해도 됩니다.

```sh
radixscope convert FF --from 16 --to 2 8 10 16
radixscope expression "0x10 + 2#11 / 10#2" --to 2 10 16
radixscope trace "1/3" --to 2 --json
radixscope integer 127 --width 8 --signed --op add --operand 1 --json
radixscope ieee encode "1/10" --width 32
radixscope ieee decode 3F800000 --width 32
```

휠과 소스 배포 패키지는 성공한 [Quality 워크플로 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)의
산출물에서 받을 수 있습니다. 패키지 설치 방법과 Linux 데스크톱 의존성은
[설치 안내](docs/ko/install.md)를 참고하세요.

## 주요 기능

- 정수, 유한소수, 분수, `0.(3)` 같은 순환소수의 정확한 표현
- 여러 진법으로 동시 출력, 소수 자릿수 지정, 다섯 가지 반올림 방식
- `base#digits`, `0b`, `0o`, `0x`를 사용하는 혼합 진법 수식과 정확한 사칙연산
- 정수부 나눗셈과 소수부 곱셈 과정, 순환 구간 탐지
- 임의 비트 폭의 부호 있는 정수와 부호 없는 정수, 2의 보수, 비트 연산
- 범위와 오버플로 분석, 정확한 결과와 비트 폭에 맞춰 감싼 결과의 별도 표시
- 빅 엔디언·리틀 엔디언 바이트, 엄격한 ASCII 변환과 출력 가능 문자 미리보기
- 비정규수, 부호 있는 0, NaN을 포함하는 binary32·binary64 인코딩과 디코딩
- 네 가지 데스크톱 작업 화면, 결과 복사, 테마, 옵션 저장, 개수 제한이 있는 최근 기록
- 별도 프로세스에서 계산하고 취소하거나 입력 변경 시 이전 작업 중단
- 정수·IEEE 754 비트 편집과 숫자·바이트 표현의 동기화
- Python을 별도로 설치하지 않고 실행하는 Windows x64 데스크톱 ZIP

IEEE 인코딩은 정확한 유리수를 목적 형식으로 직접 반올림하며, 가장 가까운 값 중
동률이면 짝수를 선택합니다. 원시 비트 디코딩은 NaN 페이로드와 시그널링 비트를 보존합니다.
Python `float`는 이미 이진수로 반올림된 값이므로 십진 입력의 정확도가 중요하면
정확한 숫자 입력을 사용하세요.

## Python API

```python
from radixscope.core import ExactValue, convert_bases, encode_ieee754, evaluate_expression

value = evaluate_expression("0x10 + 2#11 / 10#2")
print(convert_bases(value, [2, 10, 16]))
print(encode_ieee754(ExactValue(1, 10), 32).hexadecimal)
```

## 한국어 문서

- [설치와 업데이트](docs/ko/install.md)
- [명령줄 사용법](docs/ko/cli.md)
- [데스크톱 앱 사용법](docs/ko/desktop.md)
- [숫자 처리 명세](docs/ko/specification.md)
- [2.1.0 릴리스 노트](docs/ko/releases/2.1.0.md)

정확한 진법 변환 결과의 순환 주기는 매우 길 수 있습니다. 명령줄의 정확한 출력에는
길이 제한이 없으므로 출력 자릿수를 제한하려면 `--precision`을 지정하세요.
데스크톱의 정확한 변환은 소수부를 최대 1000자리까지 표시하고, 잘린 결과임을 명시합니다.
과정 화면에서는 단계 수 제한을 조절할 수 있습니다. 수식 계산과 정수 연산에는 임의 크기
정수를 사용하므로 매우 큰 거듭제곱이나 입력은 시간과 메모리를 많이 사용할 수 있습니다.

## 개발

```sh
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts packaging
python -m mypy src tests scripts packaging
python -m pytest --cov=radixscope --cov-report=term-missing
python -m build
python scripts/verify_distribution.py
```

테스트는 Ubuntu와 Windows의 Python 3.11, 3.12, 3.13에서 실행합니다.
Qt 테스트는 화면 없는 offscreen 플랫폼을 사용합니다. Quality 워크플로는 휠과 소스
아카이브를 빌드하고, 독립된 환경에서 설치를 검증한 뒤 패키지를 산출물로 저장합니다.
PyPI 자동 게시는 설정되어 있지 않습니다.
Windows 데스크톱 작업은 독립 실행 ZIP도 빌드하고 검증합니다. Windows에서 직접 빌드하려면
`python -m pip install -e ".[desktop-build]"`로 설치한 뒤
`python scripts/build_desktop.py`, `python scripts/verify_desktop.py`를 순서대로 실행하세요.
