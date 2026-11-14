# RadixScope

한국어 | [English](README.md)

<img src="src/radixscope/assets/radixscope.svg" width="80" alt="RadixScope RS 아이콘">

RadixScope는 진법 변환을 중심으로 정확한 수치 계산과 숫자 표현 분석을 제공하는
데스크톱 도구입니다. Python 정수·유리수 연산으로 수학적 값을 보존하면서,
고정 비트 정수와 부동소수점이 실제로 어떻게 인코딩되는지 살펴볼 수 있습니다.
Core 기능은 CLI와 Python API로도 사용할 수 있습니다.

## 기능

| 작업 화면 | 주요 기능 |
| --- | --- |
| 진법 변환 | 2~36진법 변환, 분수·순환소수·과학적 표기법, 다섯 반올림 방식 비교, 변환 과정, 진법 프리셋과 원본·대상 교환 |
| 수치 계산 | 혼합 진법 수식과 고정 비트 정수 연산, 정확한 결과·오버플로·래핑 구분, 비트 범위 추출과 최소 비트 폭 분석 |
| 숫자 분석 | 진법별 값, Signed/Unsigned, 비트·엔디언 바이트 표현, 비트·Hex 편집, 부동소수점 분석, 숫자 비교와 연산 실험 |
| 일괄 변환 | 숫자·수식을 줄 단위로 처리하고 개별 오류를 유지하며 결과 내보내기 |

부동소수점은 binary16·bfloat16·binary32·binary64를 지원합니다. 정확한 표현 오차,
ULP, 인접 값, 부호 있는 0과 NaN 페이로드를 확인할 수 있습니다.
연산 실험은 피연산자를 먼저 반올림한 결과와 정확히 계산한 뒤 한 번 반올림한 결과를 비교합니다.

GUI는 한국어·영어, 라이트·다크·시스템 테마, 기록 검색, 개별 결과 복사와
텍스트·JSON·CSV 내보내기를 지원합니다. 계산은 취소 가능한 별도 프로세스에서 수행하며,
입력이 바뀌면 이전 결과를 무효화합니다.

## 소스에서 실행

Python 3.11 이상으로 저장소 폴더에서 실행합니다.

```sh
python -m pip install ".[gui]"
python -m radixscope.gui
```

별도 실행 의존성이 없는 Core·CLI만 필요하면 `python -m pip install .`로 설치합니다.
설치 후 `radixscope`, `radixscope-gui` 명령을 사용할 수 있습니다.

GUI에서는 진법 변환에 `1/3`을 입력하고 **변환 과정 보기**를 선택해 보세요.
숫자 분석에서는 8비트 정수 `255` 또는 `binary16`의 `0.1`을 살펴볼 수 있습니다.
**분석 방식**에서 부동소수점 형식 비교, 숫자 비교, 부동소수점 연산 실험을 선택합니다.

## CLI

```sh
python -m radixscope convert FF --from 16 --to 2 8 10 16
python -m radixscope expression "(0xFF & 0x0F) << 2"
python -m radixscope integer 256 --width 8 --requirements
python -m radixscope inspect FF --base 16 --width 8 --signed --pattern
python -m radixscope compare-numbers 255 127 --width 8 --json
python -m radixscope float-op add 0.1 0.2 --format binary16 --json
```

각 명령의 `--help`로 옵션을 확인할 수 있습니다.
입력 문법은 [CLI 문서](docs/ko/cli.md), Python 사용법은
[수치 모델과 API](docs/ko/specification.md)를 참고하세요.

## Windows 프로그램

Windows에서 x64 Python 3.11 이상을 `python` 명령으로 사용할 수 있어야 합니다.

```powershell
.\build_windows.bat
```

설치된 빌드 의존성을 재사용하고, 필요한 경우에만 설치한 뒤 프로젝트 루트에
`RadixScope.exe`를 만듭니다. `_internal/`을 EXE 옆에 유지하세요.
해당 런타임 폴더에는 Python과 Qt 실행 환경이 포함됩니다.

## 문서

- [설치와 실행](docs/ko/install.md)
- [데스크톱 사용법](docs/ko/usage.md)
- [CLI](docs/ko/cli.md)
- [수치 모델과 Python API](docs/ko/specification.md)

