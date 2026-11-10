# RadixScope

한국어 | [English](README.md)

RadixScope는 정확한 수 계산, 고정 비트 정수, 부동소수점 정밀도, 바이트와 비트필드를
분석하는 데스크톱·명령줄 도구입니다. CLI와 PySide6 GUI가 같은 Python Core를 사용합니다.

## 설치와 실행

Windows x64에서는 성공한
[Quality 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)의
`RadixScope-windows-x64` 산출물을 내려받으세요. 산출물 압축을 풀면 설치 파일과
압축형 패키지가 있습니다. 설치형은 바로가기와 제거 프로그램을 제공합니다.
압축형은 내부 ZIP까지 푼 뒤 `RadixScope/RadixScope.exe`를 실행하며,
`_internal`을 포함한 폴더 전체를 함께 유지해야 합니다. 두 형태 모두 Python과 Qt를 포함합니다.

Python 3.11 이상이 설치된 환경에서는 저장소 폴더에서 실행하세요.

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

Core와 CLI만 설치하려면 `python -m pip install .`을 사용합니다. 별도 실행 의존성이 없습니다.
설치 후 `radixscope`, `radixscope-gui` 명령을 사용할 수 있습니다.
가상환경, Linux 라이브러리, 업데이트, 휠 설치와 직접 빌드 방법은
[설치 안내](docs/ko/install.md)에 정리되어 있습니다.

## 주요 기능

- 2~36진법의 정확한 변환, 분수·순환소수·십진 과학적 표기법
- 사칙연산·몫·나머지·비트 연산·시프트를 지원하는 정확한 수식 계산
- 숫자·부호·비트·엔디언 바이트 표현을 함께 다루는 Number Inspector
- 정확한 결과·오버플로·래핑 결과를 구분하는 고정 비트 정수 연산
- binary16·bfloat16·binary32·binary64 인코딩, 원시 패턴 디코딩과 형식 비교
- 유리수 기반 오차, ULP 간격, 인접 값, 비정규수 경계와 NaN 페이로드 분석
- Hex·Binary·Base64·UTF-8 바이트 입력, 범위 선택, ASCII 미리보기와 비트필드 레이아웃
- XOR, 변경 비트·바이트와 필드별 차이를 보여주는 패턴 비교
- 일괄 변환, 기록 검색, 결과 재사용과 텍스트·JSON·CSV 내보내기
- 한국어·영어 GUI, 라이트·다크 테마, 비트 편집과 취소 가능한 계산 프로세스

원시 재해석은 비트를 보존하며, 수치 변환은 목적 형식이 허용하는 범위에서 수학적 값을
옮깁니다. IEEE 인코딩은 정확한 유리수를 목적 형식으로 직접 반올림하며 동률이면 짝수를
선택합니다. Python `float`는 이미 이진수로 반올림된 값이므로 정확한 십진 입력에는
문자열이나 `ExactValue`를 사용하세요.

## CLI 예시

```sh
radixscope convert FF --from 16 --to 2 8 10 16
radixscope convert "1.25e-3" --auto --to 10 16
radixscope expression "(0xFF & 0x0F) << 2" --to 2 10 16
radixscope trace "1/7" --to 2 --max-steps 12 --json
radixscope inspect FF --base 16 --width 8 --signed --pattern
radixscope integer 127 --width 8 --signed --op add --operand 1
radixscope ieee encode "1/10" --format bfloat16 --json
radixscope ieee compare "1/10"
radixscope bytes "3F 80 00 00" --byteorder big
radixscope compare "FF 00" "FE 80" --json
radixscope batch --file numbers.txt --mode auto --to 2 10 16 --csv
```

모든 명령에 `--help`, `--json`이 있습니다. 일괄 변환 CSV에는 입력별 오류가 포함됩니다.
자세한 옵션은 [CLI 안내](docs/ko/cli.md)를 참고하세요.

## Python API

```python
from radixscope.core import (
    ExactValue, convert_bases, encode_ieee754, evaluate_expression, inspect_number,
)

value = evaluate_expression("0x10 + 2#11 / 10#2")
assert value == ExactValue(35, 2)
print(convert_bases(value, [2, 10, 16]))
print(encode_ieee754(ExactValue(1, 10), "binary16").hexadecimal)
assert inspect_number("FF", base=16, width=8, signed=True, raw=True).exact == ExactValue(-1)
```

## 문서와 개발

- [설치와 패키징](docs/ko/install.md)
- [명령줄 사용법](docs/ko/cli.md)
- [데스크톱 작업 화면과 기록](docs/ko/desktop.md)
- [수치 모델·API·작업 한도](docs/ko/specification.md)

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python scripts/verify_numeric.py
python -m radixscope.gui.verification
python -m build
```

Quality는 Ubuntu와 Windows의 Python 3.11~3.13에서 검사하고 휠·소스 패키지를 빌드합니다.
Windows 데스크톱은 압축 해제 후 실행, 설치 후 실행과 제거까지 검증합니다.
산출물은 Actions 실행에 첨부됩니다.

정확한 계산에도 작업 한도는 있습니다. 전개·거듭제곱·과정·바이트 버퍼·일괄 입력에
각각 한도를 적용합니다. GUI는 부분 전개를 명시하며, 제한 때문에 원래 유리수를
자동으로 바꾸지는 않습니다. 구체적인 기준은 수치 처리 명세를 참고하세요.
