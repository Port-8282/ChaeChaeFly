# 인프라 실행 명세

> 로컬 개발용 Compose 기준이다. 운영 서버·Jenkins 배포 설정은 아직 구현 전이다.

## 서비스·포트

레포는 ChaeChaeFly, 기본 Compose 프로젝트 이름은 `port8282`다. 공통 `compose.yaml`과 개발 `compose.dev.yaml`을 함께 실행한다.

| 서비스 | 실행 환경 | 컨테이너 포트 | 현재 역할 |
| --- | --- | --- | --- |
| proxy | Nginx 공식 이미지 | 8080 | 호스트 127.0.0.1:8282의 화면/API 진입점 |
| front | Vue 3.5.44·Vite 8.3.5 / Node 24.18.0·npm 11.16.0 | 8080 | 개발용 Vite 기본 화면 |
| back | Spring Boot 4.1.2 / JDK 21·Gradle 9.8.2 | 8080 | 상태 확인 API·JDBC DB 연결 |
| ai | Python 3.12.13·uv 0.12.14 / FastAPI·Uvicorn | 8000 | 최소 상태 확인 API |
| ml | Python 3.12.13·uv 0.12.14 / FastAPI·Uvicorn | 8000 | 최소 상태 확인 API, 모델 미포함 |
| db | PostgreSQL 17.11-bookworm | 5432 | 앱 데이터 저장소, 업무 테이블 미생성 |

Proxy 이외의 호스트 포트는 열지 않는다. 개발용 4개 앱은 UID 10001, Proxy는 공식 Nginx의 UID 101로 실행한다. DB는 공식 이미지의 초기화·사용자 전환 방식을 사용한다. 모델 학습 환경은 보류한다.

## 네트워크·상태 확인

- `web`: Proxy·Front·Back.
- `application`: Back·AI·ML. AI의 향후 LLM 외부 연결을 허용한다.
- `database`: Back·DB만 참여하는 internal 네트워크.
- Back은 DB의 앱 계정 인증·`SELECT 1` healthcheck가 통과한 뒤 시작한다.
- Proxy는 Front·Back healthcheck가 통과한 뒤 시작한다. 실행 중 재연결·업무 재시도 정책은 앱에서 별도로 구현한다.
- 외부 `/health`는 Proxy만 확인한다. `/api/health`는 Back의 `/actuator/health`로 연결하고 `compose` 프로필에서는 JDBC DB 상태도 포함한다. 상세 연결 정보는 공개하지 않는다.
- AI·ML `/health`는 HTTP 프로세스 확인이며 실제 최적화·추론 준비 상태가 아니다.

## 환경변수 소유 범위

루트 `.env`는 Compose가 읽고 필요한 값만 각 서비스에 전달한다. 예시를 그대로 사용할 수 있는 범위는 로컬 개발이며 실제 비밀번호·LLM 키는 Git에 넣지 않는다.

| 변수 | 사용 위치 | 기본 의미 |
| --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | Compose | 기본 `port8282`, 리소스 이름 구분 |
| `APP_PORT` | Proxy 포트 연결 | 기본 8282 |
| `TZ` | Back·AI·ML·DB | 기본 Asia/Seoul |
| `POSTGRES_DB` | DB·Back URL | 기본 port8282 |
| `POSTGRES_PASSWORD` | DB만 | 관리자 postgres 비밀번호 |
| `DB_APP_USER`, `DB_APP_PASSWORD` | DB 초기화·Back | 별도 앱 계정과 비밀번호 |
| `LLM_API_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | AI만 | 향후 LLM 연결, 현재 비워 둘 수 있음 |

Compose는 Back에 `SPRING_PROFILES_ACTIVE=compose`와 `SPRING_DATASOURCE_URL/USERNAME/PASSWORD`를 전달한다. `AI_BASE_URL=http://ai:8000`, `ML_BASE_URL=http://ml:8000`은 향후 업무 호출용으로 전달하며 아직 앱 호출 코드는 없다. 개발 Front의 `BACKEND_URL`은 `http://back:8080`이다.

호스트에서 직접 실행하면 Front는 기본 5173, Back은 8080이다. Back의 기본 `local` 프로필은 DB 없이 실행한다. 호스트용 포트·환경변수 사용법은 [로컬 개발 안내](local-setup.md)를 따른다.

## 저장소

- `postgres_data`: PostgreSQL 17의 `/var/lib/postgresql/data`. 기본 실제 이름은 `port8282_postgres_data`이며 프로젝트 이름에 따라 달라진다.
- `gradle_cache`: 개발 Back의 `/home/app/.gradle`. 라이브러리 다운로드 캐시.
- 일반 `down`은 두 볼륨을 보존한다. DB 백업·복원은 영속 볼륨과 별도 절차다.
- DB 초기화 스크립트는 빈 데이터 볼륨에만 적용한다. 환경변수 변경만으로 기존 DB 계정이 갱신되지는 않는다.

## 추가로 정할 항목

운영 서버·CPU·자원, Registry·모델 artifact 저장소, TLS·도메인, 실시간 업무 전달 방식, Jenkins Controller/Agent 배치와 배포·복구 정책은 미정이다. 원격 IDE·디버거 연결은 아직 자동 구성하지 않았다.

[Compose 실행 안내](compose.md) · [개별 Docker 이미지](docker.md) · [서비스 구성도](architecture.md) · [API 규격 기준](../../contracts/README.md)
