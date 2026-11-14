# 명령줄 사용법

한국어 | [English](../cli.md)

`python -m pip install .`로 설치한 뒤 `radixscope` 또는
`python -m radixscope`를 실행합니다. 모든 명령에 `--help`, `--json`이 있습니다.

## 숫자와 수식

```sh
radixscope convert FF --from 16 --to 2 8 10 16
radixscope convert "0.(3)" --to 2 10 --precision 8 --rounding half-even
radixscope convert "1.25e-3" --auto --to 10 16
radixscope expression "(0xFF & 0x0F) << 2" --to 2 10 16
radixscope expression "(7/3) // (2/3) + (-7 % 3)"
radixscope trace "1/7" --from 10 --to 2 --max-steps 12 --json
```

변환의 기본 입력은 10진수, 출력은 2·8·10·16진수입니다.
`--precision`이 없으면 순환 구간을 괄호로 표시하는 완전한 전개를 요청합니다.
작업 한도는 여전히 적용되므로 주기가 길면 자릿수나 과정 단계를 제한하세요.
반올림 방식은 `truncate`, `half-up`, `half-even`, `floor`, `ceiling`입니다.

`--auto`는 `--from`보다 우선하며 접두사, 과학적 표기, 수식과 명확한 Hex 숫자를
인식합니다. 해석이 모호하면 진법을 직접 지정하세요.
16진법의 `1E3`은 Hex 숫자이며 10진법에서는 과학적 표기입니다.
`1e`처럼 미완성인 십진 지수는 오류입니다.
과정 제한에 도달하면 `complete=false`이며 유한소수라는 뜻은 아닙니다.

수식의 `| ^ & << >> + - * / // % +x -x ~x **` 우선순위는 Python을 따릅니다.
비트 연산은 정수만 받으며 몫과 나머지는 정확한 분수도 지원합니다.
변수·함수 호출·곱셈 기호 생략은 지원하지 않습니다.

## 정수와 통합 분석

```sh
radixscope inspect FF --base 16 --width 8 --signed --pattern
radixscope inspect "0.1" --type binary16 --byteorder little
radixscope inspect 3F80 --base 16 --type bfloat16 --pattern
radixscope integer 127 --width 8 --signed --op add --operand 1 --json
radixscope integer -128 --width 8 --signed --op shr --operand 1
radixscope integer FF --base 16 --width 8 --signed --pattern
```

기본 입력은 수학적 값이고 `--pattern`은 원시 패턴 재해석입니다.
수학적 정수 입력은 선택한 범위에 들어야 합니다.
산술 연산은 정확한 결과·오버플로·명시적으로 감싼 결과를 구분합니다.
비트 연산의 피연산자는 같은 진법·폭·부호 설정을 사용하고 시프트 횟수는 10진수입니다.
부호 있는 값의 `shr`는 산술 시프트이며 `lshr`는 항상 0으로 채웁니다.
엔디언은 바이트 배열을 바꾸며 수학적 값은 바꾸지 않습니다.

## 부동소수점 분석

```sh
radixscope ieee encode "1/10" --format bfloat16 --json
radixscope ieee decode 3C00 --format binary16
radixscope ieee encode nan --format binary32 --payload 123 --signaling
radixscope ieee encode 0 --negative-zero --width 32
radixscope ieee compare "1/10" --json
```

`--format`은 binary16·bfloat16·binary32·binary64 중 선택하며 기존 `--width`
옵션(16·32·64)보다 우선합니다. 인코딩에는 정확한 수식과 부호를 붙인
`nan`, `inf`, `infinity`를 입력합니다. 디코딩은 기본적으로 16진 원시 숫자를
읽으며 `--base`로 변경합니다. 원시 디코딩은 부호 있는 0과 NaN 페이로드를 보존합니다.

보고서에는 정확한 표현값과, 정의할 수 있는 경우 유리수 기반 절대·상대 오차 및 ULP
오차, 인접 값과 경계가 포함됩니다. 비교는 같은 정확한 원본을 네 형식으로 직접
인코딩하고 중간 형식을 거치는 이중 반올림 차이도 표시합니다.
페이로드·signaling 옵션은 단일 형식의 NaN 인코딩에만 사용합니다.

## 필요한 비트 폭과 숫자 비교

```sh
radixscope integer 256 --width 8 --requirements --json
radixscope integer FF --base 16 --width 8 --extract 4 4
radixscope compare-numbers 255 127 --width 8 --json
radixscope compare-numbers "1/3" "2/3"
radixscope compare-numbers "0xFF" "0b11111111" --expressions --width 8
radixscope compare-numbers "0.1" "0.1000000001" --type binary16
```

`--requirements`는 선택 범위에 들어가지 않는 정수도 분석합니다. Signed/Unsigned 최소 폭,
선택 범위와 표준 비트 폭 수용 여부를 표시하며, 연산·원시 패턴 옵션과 함께 사용하지 않습니다.
`--extract OFFSET WIDTH`는 결과의 LSB 0 기준 범위를 추출하고 선택한 부호 해석을 적용합니다.

`compare-numbers`는 두 입력에 공통 진법·자료형·폭·부호 옵션을 사용합니다.
대소 관계와 차이는 정확한 원본 값으로 계산하고 부동소수점 패턴은 따로 반올림합니다.
분수나 범위 밖 정수도 비트 패턴 없이 수학적으로 비교할 수 있습니다.
호환되는 패턴에는 XOR, Signed/Unsigned 해석과 다른 비트 위치를 표시합니다.
NaN은 `unordered`이며 무한대 피연산자에는 유한한 차이를 부여하지 않습니다.
위치 목록은 최대 4096개이고 `positions_complete`로 전체 목록인지 구분합니다.

## 부동소수점 연산 실험

```sh
radixscope float-op add 0.1 0.2 --format binary16 --json
radixscope float-op subtract "1 + 1/1000" 1 --format bfloat16
radixscope float-op divide 1 0 --format binary32
radixscope float-op add 7C01 3C00 --patterns --format binary16
```

`float-op`는 add·subtract·multiply·divide를 지원합니다. 숫자는 정확한 수식으로 입력하고,
`--patterns`는 두 값을 선택 형식의 원시 패턴으로 디코딩합니다. 원시 진법 기본값은 16입니다.
네 형식 모두 가장 가까운 값, 동률이면 짝수로 반올림합니다.

`rounded_operands`는 두 입력을 먼저 인코딩한 뒤 연산 결과를 반올림하고,
`exact_then_round`는 원래 값을 정확히 계산한 뒤 한 번 반올림합니다.
원래 정확한 입력, 인코딩된 피연산자, 입력 변환 플래그, 연산 플래그,
연산 자체의 반올림 오차와 원래 수학적 값과의 오차를 구분합니다.
오버플로·언더플로·유효하지 않은 연산·0으로 나눔·정확하지 않음을 별도 플래그로 표시합니다.
특수값과 NaN 전파는 [수치 규칙](specification.md#부동소수점-연산)을 따릅니다.

## 일괄 변환과 내보내기

```sh
radixscope batch --file numbers.txt --mode auto --to 2 10 16 --csv
radixscope batch --file numbers.txt --mode expression --exact --json
radixscope batch - --mode number --from 16 --limit 100 --csv
```

파일은 UTF-8이며 BOM도 허용합니다. `--file` 없이 `-`를 사용하면 표준 입력을 읽고,
여러 줄 문자열을 직접 전달할 수도 있습니다. 빈 줄은 건너뛰고 원래 줄 번호를 유지합니다.
모드는 number·expression·auto입니다. 기본 출력은 소수부 16자리이며,
`--exact`는 작업 한도 안에서 완전한 전개를 요청합니다.

잘못된 줄은 해당 행의 오류로 남기고 다른 결과는 유지합니다.
전체 옵션이나 입력 크기 오류는 명령 오류입니다. 일괄 명령이 성공하더라도
`errors`, `limited`와 행별 오류를 확인하세요.
최대 1000행, 서식화된 일괄 결과 2 MiB까지 처리합니다.

JSON의 기존 보고서 키는 유지합니다. 일반 숫자 필드는 JSON 숫자이며, Python의 현재
십진 문자열 변환 한도를 넘는 정수만 정확한 십진 문자열로 출력합니다.
정확한 유리수는 문자열입니다. GUI의 텍스트·JSON·CSV 내보내기도 언어 설정과 무관하게
같은 원본 보고서 데이터를 사용합니다.

## 종료 코드와 음수 인자

성공 시 0, 잘못된 인자나 숫자는 2이며 오류를 stderr에 출력합니다.
계산 중 Ctrl+C는 130을 반환합니다. 옵션처럼 보이는 음수는 옵션을 먼저 적고
`--` 뒤에 입력하세요.

```sh
radixscope ieee encode --width 32 -- -inf
radixscope integer --base 16 --width 8 --signed -- -7F
```
