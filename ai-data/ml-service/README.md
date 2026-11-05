# ML 추론 서비스

검증된 전처리와 모델을 시작 시 로드하고, AI가 보낸 데이터에 대해 하역시간 예측값을 반환한다. 학습은 여기서 수행하지 않는다.

- 내부 HTTP + JSON 통신을 기본안으로 한다. 컨테이너 포트는 8000이며 예측 경로·요청·응답은 API 합의 후 추가한다.
- 입력 특징, 결측값 처리, 단위, 응답 모델 버전·전처리 버전을 명시한다.
- 모델과 전처리 로드가 끝나고 추론 가능한 상태가 된 뒤 준비 완료로 응답한다.
- 요청한 모델 버전을 사용할 수 없으면 명확한 오류를 반환한다. 다른 버전으로 몰래 계산하지 않는다.
- 모델 artifact의 위치·SHA256·평가 결과를 검증한 뒤 이미지에 포함한다.
- 큰 모델 파일은 Git에 넣지 않는다. 검증된 모델 저장소에서 빌드 시 가져온다.

`port8282_ml` 패키지와 독립 uv 환경, FastAPI·Uvicorn 실행 진입점과 Dockerfile을 구성했다. 현재 API는 프로세스 상태를 확인하는 `GET /health`뿐이며 예측 API·모델은 아직 없다. 모델 종류와 필요한 추론 라이브러리는 ML 담당자가 정한 뒤 추가한다. 모델 교체는 ML 이미지를 갱신하는 배포이며 AI와의 호환 테스트를 포함한다.

## 개발 환경

Python 3.12.13, uv 0.12.14 이상을 사용한다. 이 폴더에서 실행한다.

```bash
uv sync --locked
uv run --locked python -c "import port8282_ml; print(port8282_ml.__file__)"
uv run --locked ruff check src
uv run --locked ruff format --check src
```

실행용 의존성은 FastAPI 0.162.0·Uvicorn 0.54.0이며 정확한 하위 의존성은 `uv.lock`으로 고정한다. `pytest`·`ruff`는 개발 도구다. AI 환경의 라이브러리를 가져다 쓰지 않는다. 하위 Python 패키지를 추가할 때는 `__init__.py`도 둔다.

모델을 연결할 때 모델 파일·버전, 전처리 방식, 추론 라이브러리·버전, 입력·출력 형식을 함께 확인한다. 테스트를 작성한 뒤 `uv run --locked pytest`로 실행한다. 현재 테스트 없음(exit 5)은 성공이 아니다. 자세한 절차는 [로컬 개발 안내](../../docs/infra/local-setup.md)를 참고한다.

## API 실행

이 폴더에서 실행한다. `--reload`는 로컬 개발에만 사용한다.

```bash
uv run --locked uvicorn port8282_ml.api.main:app --host 127.0.0.1 --port 8002 --reload
```

`http://127.0.0.1:8002/health` → `{"status":"ok","service":"ml"}`

**`/health`는 HTTP 서버의 생존 확인이다. 모델이 로드되었거나 예측할 수 있다는 뜻이 아니다.** 모델을 연결할 때는 모델·전처리 로드를 확인하는 별도 준비 상태 검사를 추가한다. 현재 모델이 없는 상태를 예측 준비 완료로 표시하지 않는다.

## Docker 단독 실행: 빌드된 버전 확인

**저장소 루트**에서 실행한다. Docker가 설치되어 실행 중이면 호스트에 Python·uv를 설치하지 않아도 빌드할 수 있다. 첫 빌드에는 인터넷 연결이 필요하다.

```bash
docker build -t port8282-ml:local ./ai-data/ml-service
docker run --rm --name port8282-ml-local -p 127.0.0.1:8002:8000 port8282-ml:local
```

브라우저에서 같은 `/health` 주소를 확인한다. 종료는 Ctrl+C다. 다른 터미널에서는 `docker stop port8282-ml-local`을 사용한다.

- 빌드 단계: Python 3.12.13·uv 0.12.14로 `uv.lock`에 맞는 실행용 환경을 만든다.
- 실행 단계: 설치된 환경만 복사하고 일반 사용자 UID 10001로 실행한다. uv·pytest·Ruff는 실행 이미지에 넣지 않는다.
- 컨테이너 내부 포트는 8000, 단독 확인용 호스트 포트는 8002다. AI와 별도 컨테이너라 내부 포트가 같아도 충돌하지 않는다.
- 모델·`build-assets/`·호스트 `.venv`는 현재 이미지에 복사하지 않는다. 모델을 연결할 때 검증한 artifact만 명시적으로 복사하는 단계를 추가한다.
- 소스를 수정하면 이미지를 다시 빌드한다. 로컬 개발 명령과 달리 자동 새로고침은 없다.
- GPU·CUDA·학습 패키지는 포함하지 않았다. 실제 모델에 필요한 CPU/GPU 환경은 모델 담당자와 확정한다.

태그와 함께 공식 이미지의 multi-platform digest를 고정했다. 기반 이미지 보안 업데이트는 digest를 갱신하고 다시 빌드·검증한다. Dockerfile은 [uv Docker 안내](https://docs.astral.sh/uv/guides/integration/docker/)와 [FastAPI 컨테이너 안내](https://fastapi.tiangolo.com/deployment/docker/)를 기준으로 작성했다.

## Compose로 개발하기

개발용 Compose는 Dockerfile의 `development` 단계를 사용한다. **저장소 루트**에서 전체 환경을 실행한다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

호스트에 Python·uv를 설치하지 않아도 된다. Compose Watch가 `src/`의 변경을 컨테이너 `/app/src`로 전달하고 Uvicorn이 Python 코드 변경을 감지해 다시 시작한다. 테스트 파일은 `/app/tests`로 전달한다. `.python-version`, `pyproject.toml`, `uv.lock` 변경은 이미지 재빌드가 필요하며 Watch 설정이 이를 처리한다. 일반 `up`만 실행하면 파일 동기화는 시작하지 않는다.

다른 터미널에서 실행 중인 개발 컨테이너에 검사 명령을 보낸다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec ml uv run --locked ruff check src tests
docker compose -f compose.yaml -f compose.dev.yaml exec ml uv run --locked ruff format --check src tests
docker compose -f compose.yaml -f compose.dev.yaml exec ml uv run --locked pytest
```

현재 테스트는 아직 없으므로 pytest의 exit 5를 통과로 기록하지 않는다. 실제 기능 테스트를 추가한 뒤 사용한다. 개발 이미지는 uv·pytest·Ruff와 수정 가능한 소스를 포함하지만, 기본 `docker build`로 만드는 최종 `runtime` 이미지는 계속 실행용 의존성만 포함한다.

호스트 `.venv`를 컨테이너에 연결하지 않는다. 컨테이너에서 실행하는 `uv run --locked`는 설치된 의존성을 확인하며, 라이브러리를 바꾸려면 Git으로 공유할 `pyproject.toml`·`uv.lock`까지 함께 갱신해야 한다. 모델·업무 기능 준비 완료 검사는 이번 환경 구성 범위에 포함되지 않는다.
