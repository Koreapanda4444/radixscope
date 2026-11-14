# 개발·검증·빌드

한국어 | [English](../development.md)

## 소스 구조

| 위치 | 역할 |
| --- | --- |
| `src/radixscope/core/` | 의존성 없는 정확한 수치 모델과 공개 API |
| `cli.py`, `reports.py`, `exports.py` | CLI 명령·공통 리포트·직렬화 |
| `calculations.py`, `worker.py` | 계산 요청과 취소 가능한 프로세스 실행 |
| `src/radixscope/gui/` | PySide6 작업 화면·번역·표시 |
| `settings.py` | 기존 형식을 유지하는 GUI 설정·기록 저장 |
| `src/radixscope/assets/` | 패키지에 포함하는 앱 아이콘·컨트롤 SVG·한국어 번역 |
| `scripts/`, `packaging/` | 검증·빌드 진입점과 데스크톱 실행·설치 입력 파일 |

공개 Core API와 CLI는 Qt에 의존하지 않습니다. 공통 리포트로 CLI·GUI 내보내기의
일관성을 유지하며 GUI 모듈을 Core에 넣지 않습니다.
`gui/verification.py`는 패키징한 EXE의 `--self-check`에서도 사용하므로 패키지에
유지합니다. 빌드 시점 검사는 `scripts/`에 둡니다.

## 소스 검증

```sh
python -m pip install -e ".[dev]"
python -m ruff check src scripts packaging
python -m mypy src scripts packaging
python scripts/verify_numeric.py
python -m radixscope.gui.verification
python -m build
python scripts/verify_repository.py --packages
```

`verify_numeric.py --exhaustive`는 모든 16비트 부동소수점 패턴도 확인합니다.
GUI 검증은 임시 설정으로 두 언어·전체 작업 화면·전달·취소·내보내기·상태 복원을
확인합니다. 저장소 검증은 문서 내부 링크·Python/CLI 예시·패키지 리소스를 확인합니다.
데스크톱이 없는 환경에서는 `QT_QPA_PLATFORM=offscreen`을 지정하세요.

## CI와 생성물

`.github/workflows/quality.yml`은 Ubuntu·Windows의 Python 3.11~3.13에서 Quality를
실행합니다. 후속 Windows 데스크톱 작업은 Python 3.12 x64를 사용합니다.
데스크톱 빌드가 전체 품질 검사에 의존하므로 통합 워크플로를 유지합니다.
검증은 임시 데이터를 사용하며 빌드 출력·검증 결과·캐시·로컬 환경은 Git에서 제외합니다.
아이콘·번역은 패키지 리소스로 유지합니다. 제품 버전·Windows 메타데이터는 기존 값을 사용합니다.

## 직접 빌드와 검증

Windows x64의 Python 3.12 환경을 사용합니다. 설치형에는 Inno Setup 6.3 이상이 필요하며,
`ISCC`를 PATH에 추가하거나 기본 Inno Setup 6 설치 경로를 사용하세요.

```sh
python -m pip install -e ".[desktop-build]"
python scripts/build_desktop.py --installer
python scripts/verify_windows.py
```

`--installer`를 빼면 압축형 ZIP만 빌드합니다. 결과는 `dist/`에 생성합니다.
PyInstaller로 런타임을 묶고, 빌드 스크립트는 의존성의 라이선스 파일을
`licenses/`에 보존합니다.

검증은 실제 ZIP을 임시 경로에 풀어 모든 화면을 실행하고, 다른 임시 경로에 설치한 앱에서
같은 검사를 수행한 뒤 제거합니다. 한국어·영어 상태, 취소, 설정, 런타임과 아이콘을 확인합니다.
JSON 결과와 설치 로그는 `build/desktop/verification/`에 저장하며,
CI에서는 `Windows-distribution-verification` 산출물로 제공합니다.
CI는 Windows EXE 제품 메타데이터도 확인합니다.
