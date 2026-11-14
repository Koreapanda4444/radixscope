# RadixScope

RadixScope는 정확한 수 계산, 고정 비트 정수, 부동소수점 정밀도, 바이트와 비트필드를
분석하는 Python·PySide6 데스크톱·명령줄 도구입니다.

한국어 | [English](README.md)

## 주요 기능

- 2~36진법의 정확한 변환, 분수·순환소수·과학적 표기법
- 정확한 수식 계산, 변환 과정과 오버플로 분석을 포함한 고정 비트 정수 연산
- 수치·원시 비트·엔디언 바이트 표현을 동기화하는 Number Inspector
- binary16·bfloat16·binary32·binary64 인코딩·디코딩·정밀도 비교
- 유리수 기반 오차, ULP 간격, 인접 값, 비정규수 경계와 NaN 페이로드 분석
- Hex·Binary·Base64·UTF-8 바이트 입력, 비트필드 레이아웃 저장과 패턴 비교
- 일괄 변환, 기록 검색, 결과 재사용과 텍스트·JSON·CSV 내보내기
- 한국어·영어, 라이트·다크·시스템 테마와 취소 가능한 계산

## 설치와 실행

저장소 폴더에서 Python 3.11 이상을 사용합니다.

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

별도 실행 의존성이 없는 Core·CLI는 `python -m pip install .`로 설치하고 실행합니다.

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
```

설치 후 `radixscope`, `radixscope-gui` 명령도 사용할 수 있습니다.
Windows x64 패키지는 성공한
[Quality 실행](https://github.com/Koreapanda4444/radixscope/actions/workflows/quality.yml)의
`RadixScope-windows-x64` 산출물에서 받을 수 있습니다.
설치형·압축형 실행 방법은 설치 안내를 참고하세요.

## 문서

- [설치·업데이트·데이터 위치](docs/ko/install.md)
- [데스크톱 사용법](docs/ko/usage.md)
- [명령줄 사용법](docs/ko/cli.md)
- [수치 모델·Python API·작업 한도](docs/ko/specification.md)
- [개발·검증·빌드](docs/ko/development.md)

원시 재해석은 비트를 보존하며 수치 변환은 목적 형식의 규칙을 따릅니다.
정확한 십진 입력에는 문자열이나 `ExactValue`를 사용하세요. 출력·작업 한도는
명시적으로 표시하며 저장한 유리수를 자동으로 바꾸지 않습니다.

## 개발

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python scripts/verify_numeric.py
python -m radixscope.gui.verification
```

기존 검증은 임시 데이터를 사용합니다. Quality는 Ubuntu·Windows의 Python 3.11~3.13,
Python 배포 패키지와 Windows 데스크톱 빌드의 설치·제거까지 확인합니다.
빌드 명령은 개발 안내를 참고하세요.
