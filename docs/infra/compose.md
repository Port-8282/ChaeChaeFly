# Compose로 함께 개발하기

공통 설정 `compose.yaml`과 개발 설정 `compose.dev.yaml`을 합쳐 6개 서비스를 실행한다. 현재는 기본 화면·상태 확인 API와 Back의 PostgreSQL 연결까지 구성했다. 스케줄 계산·추론·보고서 업무 흐름과 Jenkins 배포는 아직 구현 전이다.

## 파일 역할

| 파일 | 내용 |
| --- | --- |
| `compose.yaml` | 서비스·내부 네트워크·DB 영속 볼륨·환경변수·시작 조건 |
| `compose.dev.yaml` | Dockerfile의 development target·Watch 규칙·Gradle 캐시 |
| `infra/proxy/nginx.conf` | 화면/API 경로 전달·개발용 WebSocket 연결 |
| `infra/db/init/10-app-user.sh` | DB 최초 생성 시 앱 전용 계정 생성 |
| `.env.example` | 로컬 `.env` 작성 기준 |

공통 파일만 실행하면 `:local` 실행 이미지를 사용한다. 이 문서의 팀 개발 방식은 두 파일을 함께 사용해 `:dev` 이미지를 빌드한다. 서버용 `compose.prod.yaml`은 아직 없다.

## 처음 시작하기

Docker Desktop을 Linux 컨테이너 모드로 실행하거나, Linux에서 Docker Engine·BuildKit·Compose를 준비한다. Compose **2.32.0 이상**을 사용한다. 호스트에 Node.js·JDK·uv를 별도로 설치하지 않아도 된다.

아래 명령은 모두 **저장소 루트**에서 실행한다. 처음 한 번 `.env.example`을 `.env`로 복사한다. 이미 `.env`가 있다면 덮어쓰지 않고 빠진 항목만 추가한다.

```bash
# macOS·Linux
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

예시 비밀번호는 공개된 로컬 개발값이다. 실제 비밀값은 `.env`에만 두고 Git에 올리지 않는다. LLM 값은 아직 기능이 없어 비워 둘 수 있다.

```bash
docker compose version
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

첫 실행은 이미지·라이브러리 다운로드 때문에 시간이 걸린다. Watch가 실행 중인 터미널을 유지한다. 개발 포트 8282가 사용 중이면 `.env`의 `APP_PORT`를 바꾸고 해당 주소로 접속한다.

## 접속 경로와 현재 의미

```text
브라우저 → Proxy :8282
             ├─ 화면 → Front :8080
             └─ /api → Back :8080 → PostgreSQL :5432

향후 업무 연결: Back → AI :8000 → ML :8000
```

| 주소 | 현재 확인 내용 |
| --- | --- |
| `http://127.0.0.1:8282` | Vue 기본 화면 |
| `http://127.0.0.1:8282/health` | Proxy 프로세스 상태 |
| `http://127.0.0.1:8282/api/health` | Back 상태와 JDBC를 통한 DB 연결 상태 |

`/api/health`만 내부 `/actuator/health`로 연결한다. 다른 `/api` 경로는 그대로 Back으로 전달하며 아직 업무 API는 없다. 외부 `/actuator` 접근은 차단한다. AI·ML의 `/health`는 프로세스 확인이며 모델 준비·최적화 성공을 뜻하지 않는다.

Proxy의 호스트 포트만 127.0.0.1에 연결한다. AI·ML·DB는 호스트 포트를 열지 않는다. 앱 간 주소에는 `ai`, `ml`, `db` 같은 서비스 이름을 사용한다. 컨테이너 안의 localhost는 그 컨테이너 자신이다.

## 코드 수정과 검사

| 변경 대상 | Watch 동작 |
| --- | --- |
| Front 소스·정적 파일 | 동기화 후 Vite가 반영 |
| AI·ML Python 소스 | 동기화 후 Uvicorn이 다시 로드 |
| Back 소스·설정 | 동기화 후 컨테이너 재시작, Gradle 재컴파일 |
| 패키지 설정·lock·Dockerfile | 해당 이미지 재빌드·컨테이너 재생성 |

호스트 `.venv`·`node_modules`·빌드 결과는 동기화하지 않는다. 의존성을 바꿀 때는 설정과 생성된 lock 파일을 함께 갱신한다. 컨테이너 내부에서만 파일을 수정하면 호스트 Git에 자동으로 반영되지 않는다. 기존 로컬 설치 도구를 이용하는 방법은 선택 사항으로 유지하며 [서비스별 안내](../../README.md)를 따른다.

다른 터미널에서 실행 중인 개발 컨테이너 안의 도구를 사용할 수 있다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec front npm run build
docker compose -f compose.yaml -f compose.dev.yaml exec back ./gradlew --no-daemon test
docker compose -f compose.yaml -f compose.dev.yaml exec ai uv run --locked ruff check src
docker compose -f compose.yaml -f compose.dev.yaml exec ml uv run --locked ruff check src
```

Python 테스트를 추가한 뒤에는 `exec ai uv run --locked pytest`, `exec ml uv run --locked pytest`를 같은 Compose 명령 뒤에 붙여 실행한다. 현재 Python 테스트는 0개이므로 pytest exit 5를 통과로 취급하지 않는다. IDE 자동완성·원격 디버거 연결까지 자동 설정한 구성은 아니다.

## 로그·백그라운드 실행·종료

```bash
docker compose -f compose.yaml -f compose.dev.yaml ps
docker compose -f compose.yaml -f compose.dev.yaml logs -f back
docker compose -f compose.yaml -f compose.dev.yaml logs -f db
```

자동 반영 없이 한 번 실행만 확인하려면 다음을 사용한다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait
```

`-d --wait`는 상태 확인까지 기다리고 터미널을 돌려준다. Watch는 자동 시작되지 않는다. 이 상태에서 소스 자동 반영을 원하면 별도 터미널에서 `docker compose -f compose.yaml -f compose.dev.yaml watch --no-up`을 실행한다.

일반 종료는 아래 명령이다. DB 데이터와 Gradle 캐시는 남는다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml down
```

## PostgreSQL 데이터와 환경변수

PostgreSQL **17.11-bookworm**을 사용한다. 관리자 `postgres`와 앱 계정을 분리했다. Back은 기본 `port8282_app` 계정으로 접속하며 superuser 권한을 사용하지 않는다. 업무 테이블·migration은 아직 추가하지 않았다.

DB는 처음 비어 있는 `postgres_data` 볼륨을 초기화할 때 계정·DB를 만든다. **이미 초기화한 뒤 `.env`의 비밀번호·DB 이름·계정 이름만 바꾸어 재시작해도 기존 DB 값이 바뀌지 않는다.** 기존 데이터의 계정 변경은 DB에서 별도로 적용하고 앱 설정을 맞춘다. 일반 종료 과정에서 볼륨 삭제 옵션을 사용하지 않는다.

환경변수 변경은 Watch 대상이 아니므로 해당 서비스 재생성이 필요하다. 데이터 보관과 백업은 별개이며, 볼륨을 유지한다고 디스크 장애까지 복구되는 것은 아니다. 자세한 경계는 [DB 안내](../../infra/db/README.md)를 따른다.

## 검증 기록

2026-11-05, macOS arm64 + Docker Desktop의 Linux arm64 컨테이너, Compose 5.6.0에서 확인했다.

- 공통·개발 설정 병합, 서비스 6개와 Proxy 단일 호스트 포트 확인.
- 개발 이미지 4개 빌드 및 6개 컨테이너 `healthy` 확인. 기본 runtime 이미지도 다시 빌드하고 공통 Compose만으로 화면·Back/DB 상태 응답을 확인했다.
- Proxy 경유 Vue 화면·Back/DB 상태 확인, 미구현 API 404·외부 Actuator 차단 확인.
- Vite HMR WebSocket 연결과 Front 소스·정적 파일 변경 반영 확인.
- AI·ML 소스 변경 후 Uvicorn 재로딩, Back Java 소스 변경 후 재컴파일·재시작 확인.
- Back→AI와 AI→ML은 컨테이너 내부 검사 명령으로 DNS·HTTP 접근을 확인했다. 업무 호출 코드를 구현한 것은 아니다.
- PostgreSQL 17.11·비관리자 앱 계정 SQL 쓰기 확인. DB 정지 시 Back health가 503으로 바뀌고, DB 재생성 후 200으로 복구하며 기록한 데이터가 유지되는 것을 확인했다.
- 개발 컨테이너 안에서 Front 빌드, Back HTTP 테스트 1개, AI·ML Ruff 검사를 통과했다. Python 기능 테스트는 아직 없다.
- 변경 반영·장애 검증은 임시 소스 복사본과 별도 Compose 프로젝트에서 수행했다. 검증용 컨테이너·볼륨은 정리했고 기존 프로젝트 데이터는 유지했다.

Windows 호스트·Linux amd64 서버에서는 아직 직접 실행하지 않았다. 최적화·모델 추론·보고서 등 업무 통합과 운영 배포·백업 복원 검증은 별도 작업이다.

## 남은 작업

- 업무 API·스케줄링·ML·보고서 연결과 요구사항 테스트.
- 운영 서버·Registry·TLS·자원·백업 및 복구 정책.
- 서버 배포 설정과 Jenkins CI/CD.

[Docker Compose Watch](https://docs.docker.com/compose/how-tos/file-watch/) · [시작 조건](https://docs.docker.com/compose/how-tos/startup-order/) · [PostgreSQL 공식 이미지](https://hub.docker.com/_/postgres)
