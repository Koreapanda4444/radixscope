# RadixScope

한국어 | [English](README.md)

RadixScope는 정확한 수 변환과 비트 단위 분석을 위한 데스크톱·명령줄 도구입니다.
원래의 정확한 값을 유지하면서 정수·부동소수점·바이트 표현을 함께 살펴볼 수 있습니다.

## 주요 기능

- 2~36진법의 정확한 변환, 분수·순환소수와 수식 계산
- 고정 비트 정수 연산, 오버플로 분석과 비트 편집
- binary16·bfloat16·binary32·binary64 분석, 정밀도 오차와 인접 값 확인
- 바이트 분석, 비트필드 레이아웃 저장과 이진 패턴 비교
- 일괄 변환, 기록 검색과 텍스트·JSON·CSV 내보내기
- GUI·CLI·Python API, 한국어·영어 UI와 라이트·다크·시스템 테마

## 시작하기

저장소 폴더에서 Python 3.11 이상으로 실행합니다.

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

CLI만 필요하면 `python -m pip install .`로 설치합니다.

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
python -m radixscope ieee encode "1/10" --format binary32
```

설치 후 `radixscope`, `radixscope-gui` 명령도 사용할 수 있습니다.
Windows에서는 `build_windows.bat`로 `dist/RadixScope/RadixScope.exe`를 만듭니다.
`_internal/`을 포함한 프로그램 폴더 전체를 함께 보관하세요.
실행 환경·설정·업데이트는 설치 안내를 참고하세요.

## 문서

- [설치와 실행](docs/ko/install.md)
- [데스크톱 사용법](docs/ko/usage.md)
- [명령줄 사용법](docs/ko/cli.md)
- [수치 처리 규칙과 Python API](docs/ko/specification.md)

정확한 십진 입력에는 문자열이나 `ExactValue`를 사용하세요. 원시 재해석은 비트를
보존하며 수치 변환은 목적 형식의 규칙을 따릅니다. 작업 한도는 명시적으로 알리고
저장한 유리수를 자동으로 바꾸지 않습니다.
