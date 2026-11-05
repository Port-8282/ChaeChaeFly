# AI 서비스 · 계산과 최적화

Back에서 입력 상태의 스냅샷을 받아 가능한 스케줄을 평가한다. 결과와 설명용 근거를 반환하며 DB 저장은 Back에 맡긴다.

구현할 코드의 위치 제안:

```text
src/
├── port8282_ai/
│   ├── api/          # Back에 제공하는 API
│   ├── workflows/    # 고정 실행 흐름·오류 처리
│   ├── optimization/ # 접안 스케줄 탐색·최적화 알고리즘
│   ├── tools/        # 제약 검증·최적화·시뮬레이션·계산기 연결
│   ├── clients/      # ML·LLM 통신
│   └── agents/       # 근거 설명·선택 결과 보고서
└── port8282_demurrage/ # 기존 계산기 패키지 이관 위치
tests/                 # 단위 테스트·계약 규칙 검증
```

위 소스 폴더는 .gitkeep으로 준비했다. 현재 `schemas/`의 Pydantic 데이터 계약과 `tests/schemas/`의 테스트, uv 프로젝트 설정을 추가한 상태다. API·계산·탐색 실행 코드와 서버 프레임워크는 아직 없다. 전체 목표 구조는 [최종 설계안](../../docs/directory-guide.md)을 따른다.

Python 3.11 이상과 uv를 사용한다. 저장소 루트에서 서비스 디렉터리로 이동한 뒤 테스트한다.

```bash
cd ai-data/ai-service
uv sync --locked
uv run --locked pytest
```

스키마의 실행문·분기 커버리지도 함께 확인하려면 다음 명령을 사용한다.

```bash
uv run --locked pytest --cov=schemas --cov-branch --cov-report=term-missing
```

`tests/conftest.py`는 테스트마다 새로운 정상 입력·평가 데이터를 제공한다. `test_common.py`는 공통 타입과 정규화, `test_inputs.py`는 입력 참조, `test_candidates.py`는 후보와 평가 결과의 정합성, `test_schema_flow.py`는 전체 데이터 연결과 JSON 왕복을 검증한다. 계산 결과는 고정 예제로 제공하며 실제 최적화·요금 계산 알고리즘은 실행하지 않는다.

계산 한 건은 입력 상태·계약 규칙·모델 버전을 고정한다. ML 버전이 바뀌면 서로 다른 버전의 예측을 한 비교에 섞지 않는다. 실패·버전 불일치 처리에는 제한된 재시도와 종료 상태가 필요하다.

계산 결과를 먼저 반환할 수 있도록 LLM 설명·보고서 작업을 분리한다. 담당자가 자연어로 다시 질문하는 기능은 현재 범위에 없다.

기존 체선료 계산기는 예상 스케줄을 입력받는 순수 Python 패키지다. `engine.py` 하나만 옮기지 말고 전체 패키지·테스트·예제·스키마를 함께 이관한다. SOF 과거 기록은 오프라인 검산에만 사용하며 실시간 예상 비용 입력에 섞지 않는다.
