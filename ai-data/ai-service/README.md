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

`port8282_ai` 패키지와 독립 uv 환경, FastAPI·Uvicorn 실행 진입점을 구성했다. 현재 API는 프로세스 상태를 확인하는 `GET /health`만 제공한다. 스케줄링·Agent·계산 기능은 아직 없고 기존 계산기도 아직 이관하지 않았다. 전체 목표 구조는 [디렉토리 설계안](../../docs/directory-guide.md)을 따른다.

## 개발 환경

Python 3.12.13, uv 0.12.14 이상을 사용한다. 이 폴더에서 실행한다.

```bash
uv sync --locked
uv run --locked python -c "import port8282_ai; print(port8282_ai.__file__)"
uv run --locked ruff check src
uv run --locked ruff format --check src
```

실행용 의존성은 FastAPI 0.162.0·Uvicorn 0.54.0이며 정확한 하위 의존성은 `uv.lock`으로 고정한다. `pytest`·`ruff`는 개발 도구다. 라이브러리는 필요할 때 `uv add 패키지명`으로 추가하고 `pyproject.toml`·`uv.lock`을 함께 공유한다. 하위 Python 패키지를 추가할 때는 `__init__.py`도 둔다.

테스트를 작성한 뒤 `uv run --locked pytest`로 실행한다. 현재는 기능 테스트가 없으므로 테스트 없음(exit 5)은 성공이 아니다. 두 환경의 설치·검증 절차는 [로컬 개발 안내](../../docs/infra/local-setup.md)를 참고한다.

계산 한 건은 입력 상태·계약 규칙·모델 버전을 고정한다. ML 버전이 바뀌면 서로 다른 버전의 예측을 한 비교에 섞지 않는다. 실패·버전 불일치 처리에는 제한된 재시도와 종료 상태가 필요하다.

계산 결과를 먼저 반환할 수 있도록 LLM 설명·보고서 작업을 분리한다. 담당자가 자연어로 다시 질문하는 기능은 현재 범위에 없다.

기존 체선료 계산기는 예상 스케줄을 입력받는 순수 Python 패키지다. `engine.py` 하나만 옮기지 말고 전체 패키지·테스트·예제·스키마를 함께 이관한다. SOF 과거 기록은 오프라인 검산에만 사용하며 실시간 예상 비용 입력에 섞지 않는다.

## API 실행

이 폴더에서 실행한다. `--reload`는 로컬 개발에만 사용한다.

```bash
uv run --locked uvicorn port8282_ai.api.main:app --host 127.0.0.1 --port 8001 --reload
```

`http://127.0.0.1:8001/health` → `{"status":"ok","service":"ai"}`

`/health`는 HTTP 서버가 응답하는지만 확인한다. ML·LLM 연결, 최적화 성공, 체선료 계산 준비 상태는 검사하지 않는다. 업무 기능을 연결할 때 별도 준비 상태 검사를 설계한다.

## Docker 단독 실행: 빌드된 버전 확인

**저장소 루트**에서 실행한다. Docker가 설치되어 실행 중이면 호스트에 Python·uv를 설치하지 않아도 빌드할 수 있다. 첫 빌드에는 인터넷 연결이 필요하다.

```bash
docker build -t port8282-ai:local ./ai-data/ai-service
docker run --rm --name port8282-ai-local -p 127.0.0.1:8001:8000 port8282-ai:local
```

브라우저에서 같은 `/health` 주소를 확인한다. 종료는 Ctrl+C다. 다른 터미널에서는 `docker stop port8282-ai-local`을 사용한다.

- 빌드 단계: Python 3.12.13·uv 0.12.14로 `uv.lock`에 맞는 실행용 환경을 만든다.
- 실행 단계: 설치된 환경만 복사하고 일반 사용자 UID 10001로 실행한다. uv·pytest·Ruff는 실행 이미지에 넣지 않는다.
- 컨테이너 내부 포트는 8000, 단독 확인용 호스트 포트는 8001이다. ML 컨테이너도 내부 8000을 사용해도 서로 충돌하지 않는다.
- `.venv`, 비밀값, 테스트 데이터는 복사하지 않는다. 소스를 수정하면 이미지를 다시 빌드한다. 로컬 개발 명령과 달리 자동 새로고침은 없다.
- Compose에서 AI → ML 주소는 `http://ml:8000`을 사용한다. 현재 `/health`는 ML을 호출하지 않으며 업무용 서비스 연결 코드는 미구현이다.

태그와 함께 공식 이미지의 multi-platform digest를 고정했다. 기반 이미지 보안 업데이트는 digest를 갱신하고 다시 빌드·검증한다. Dockerfile은 [uv Docker 안내](https://docs.astral.sh/uv/guides/integration/docker/)와 [FastAPI 컨테이너 안내](https://fastapi.tiangolo.com/deployment/docker/)를 기준으로 작성했다.

## Compose로 개발하기

개발용 Compose는 Dockerfile의 `development` 단계를 사용한다. **저장소 루트**에서 전체 환경을 실행한다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

호스트에 Python·uv를 설치하지 않아도 된다. Compose Watch가 `src/`의 변경을 컨테이너 `/app/src`로 전달하고 Uvicorn이 Python 코드 변경을 감지해 다시 시작한다. 테스트 파일은 `/app/tests`로 전달한다. `.python-version`, `pyproject.toml`, `uv.lock` 변경은 이미지 재빌드가 필요하며 Watch 설정이 이를 처리한다. 일반 `up`만 실행하면 파일 동기화는 시작하지 않는다.

다른 터미널에서 실행 중인 개발 컨테이너에 검사 명령을 보낸다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec ai uv run --locked ruff check src tests
docker compose -f compose.yaml -f compose.dev.yaml exec ai uv run --locked ruff format --check src tests
docker compose -f compose.yaml -f compose.dev.yaml exec ai uv run --locked pytest
```

현재 테스트는 아직 없으므로 pytest의 exit 5를 통과로 기록하지 않는다. 실제 기능 테스트를 추가한 뒤 사용한다. 개발 이미지는 uv·pytest·Ruff와 수정 가능한 소스를 포함하지만, 기본 `docker build`로 만드는 최종 `runtime` 이미지는 계속 실행용 의존성만 포함한다.

호스트 `.venv`를 컨테이너에 연결하지 않는다. 컨테이너에서 실행하는 `uv run --locked`는 설치된 의존성을 확인하며, 라이브러리를 바꾸려면 Git으로 공유할 `pyproject.toml`·`uv.lock`까지 함께 갱신해야 한다. 모델·업무 기능 준비 완료 검사는 이번 환경 구성 범위에 포함되지 않는다.
