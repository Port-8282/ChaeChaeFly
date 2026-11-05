# 서비스별 Docker 빌드·실행

Front·Back·AI·ML의 Dockerfile 4개를 작성했다. 현재 실행 가능한 것은 기본 화면과 상태 확인 API다. 이 문서는 서비스별 기본 runtime 이미지 실행 방법이다. 개발용 Compose·Back의 PostgreSQL 연결은 [Compose 개발 안내](compose.md)를 따른다. 스케줄 계산·모델 추론·보고서는 구현 전이다. Jenkins CI는 [별도 안내](ci.md)를 따른다.

## Dockerfile이 하는 일

```text
Git으로 받은 소스 + 설정 + lock 파일
                  ↓
Dockerfile: 도구 설치 → 의존성 설치 → 앱 빌드
                  ↓
서비스별 이미지 생성
                  ↓
docker run: 컨테이너 실행
```

Dockerfile은 서비스 한 개를 실행할 이미지를 만드는 설명서다. Compose는 이렇게 만든 여러 서비스를 함께 실행하고 네트워크·환경변수·볼륨을 연결하는 설정이다. 공통·개발용 Compose를 추가했으며 팀 개발은 두 파일을 함께 사용한다.

| 서비스 | Dockerfile 위치 | 빌드 단계 | 실행 단계 | 내부 포트·상태 확인 |
| --- | --- | --- | --- | --- |
| Front | `front/Dockerfile` | Node 24.18.0·npm 11.16.0 → `npm ci`, Vue 빌드 | Nginx가 빌드된 화면 제공 | 8080 · `/health` |
| Back | `back/Dockerfile` | JDK 21·Gradle Wrapper → 테스트·JAR 빌드 | JRE 21에서 JAR 실행 | 8080 · `/actuator/health` |
| AI | `ai-data/ai-service/Dockerfile` | Python 3.12.13·uv 0.12.14 → `uv.lock` 잠금 설치 | FastAPI·Uvicorn | 8000 · `/health` |
| ML | `ai-data/ml-service/Dockerfile` | Python 3.12.13·uv 0.12.14 → 별도 `uv.lock` 잠금 설치 | FastAPI·Uvicorn | 8000 · `/health` |

네 서비스는 UID 10001의 비관리자 사용자로 실행한다. AI·ML의 실행 이미지에는 pytest·Ruff·uv 빌드 도구를 복사하지 않는다. ML 모델은 아직 포함하지 않았다.

기반 이미지는 태그와 digest를 함께 고정했다. 업데이트할 때 둘을 함께 변경하고 다시 검증한다. OS 패키지 다운로드 등까지 완전히 고정한 비트 단위 동일 빌드를 보장하는 구성은 아니다.

## 준비할 것

Docker Desktop을 실행하거나 Linux에서 Docker Engine과 BuildKit을 준비한다. Mac·Windows Docker Desktop은 Linux 컨테이너 모드로 사용한다. 아래 Docker 명령은 macOS 터미널과 Windows PowerShell에서 동일하다.

호스트에 Node.js·npm·JDK·uv를 따로 설치하지 않아도 이미지 안에서 준비한다. 로컬 IDE에서 직접 개발 서버를 띄우거나 검사 도구를 실행하려면 [로컬 개발 환경](local-setup.md)을 사용한다. 첫 빌드에는 이미지·패키지를 받을 인터넷 연결이 필요하다.

## 1. 이미지 빌드

**ChaeChaeFly 저장소 루트**에서 실행한다.

```bash
docker build -t port8282-front:local ./front
docker build -t port8282-back:local ./back
docker build -t port8282-ai:local ./ai-data/ai-service
docker build -t port8282-ml:local ./ai-data/ml-service
```

끝의 폴더가 build context다. 서비스 폴더의 `.dockerignore`가 적용되고 호스트의 `.venv`·`node_modules`·빌드 결과·`.env`는 제외된다. 먼저 로컬에서 npm·Gradle·uv 설치 명령을 실행할 필요가 없다. 프록시·DB는 Compose에서 공식 이미지와 설정으로 실행하므로 별도 Dockerfile이 없다. Jenkins 구성은 이후 단계다.

## 2. 서비스별로 실행

다음은 단독 상태 확인용이다. 네 서비스를 하나의 업무 흐름으로 연결하는 명령은 아니다. 모두 백그라운드로 실행하며, 이미 같은 이름을 사용 중이면 기존 용도를 확인하거나 이름을 바꾼다.

```bash
docker run -d --rm --name port8282-front-local -p 127.0.0.1:3000:8080 port8282-front:local
docker run -d --rm --name port8282-back-local -p 127.0.0.1:8080:8080 port8282-back:local
docker run -d --rm --name port8282-ai-local -p 127.0.0.1:8001:8000 port8282-ai:local
docker run -d --rm --name port8282-ml-local -p 127.0.0.1:8002:8000 port8282-ml:local
```

| 확인할 내용 | 브라우저 주소 | 기대 결과 |
| --- | --- | --- |
| Front 기본 화면 | `http://127.0.0.1:3000` | PORT 8282 기본 화면 |
| Front 상태 | `http://127.0.0.1:3000/health` | `service: front`, `status: ok` |
| Back 상태 | `http://127.0.0.1:8080/actuator/health` | `status: UP` |
| AI 상태 | `http://127.0.0.1:8001/health` | `service: ai`, `status: ok` |
| ML 상태 | `http://127.0.0.1:8002/health` | `service: ml`, `status: ok` |

`-p 127.0.0.1:8001:8000`은 **내 컴퓨터의 8001 → AI 컨테이너의 8000**을 연결한다. 다른 컨테이너인 AI와 ML은 둘 다 내부 8000을 사용해도 된다. 내 컴퓨터의 포트는 서로 다르게 지정한다. 포트가 사용 중이면 앞쪽 호스트 포트만 바꾼다.

`EXPOSE` 자체는 외부 공개가 아니다. 위 명령은 로컬 확인을 위해 127.0.0.1에만 연결한다. 현재 Compose에서는 AI·ML·DB를 내부 접근으로 두고 외부 진입점은 별도 `proxy`의 8282 포트로 묶는다.

## 3. 상태·로그 확인과 종료

```bash
docker ps
docker logs port8282-ai-local
docker inspect --format '{{.State.Health.Status}}' port8282-ai-local
```

기동 직후에는 `starting`일 수 있고 이후 검사에 통과하면 `healthy`가 된다. **Front·AI·ML의 healthy는 프로세스 상태 응답을 뜻한다. Back은 기본 local 프로필에서는 프로세스를, compose 프로필에서는 JDBC DB 연결도 확인한다. 최적화 성공·모델 로드 완료를 뜻하지 않는다.** 업무 기능 도입 시 준비 상태 검사를 따로 확장한다. Dockerfile의 HEALTHCHECK만으로 장애 컨테이너가 자동 재시작되는 것은 아니며 운영 복구 정책은 별도로 구성한다.

확인이 끝나면 다음으로 종료한다.

```bash
docker stop port8282-front-local port8282-back-local port8282-ai-local port8282-ml-local
```

위 명령으로 만든 컨테이너는 `--rm` 때문에 종료 시 삭제된다. 이미지는 다음 실행을 위해 남는다. 기존 DB 볼륨을 삭제하는 명령은 포함하지 않았다.

## 지금 되는 일과 다음 단계

- 기본 runtime Front는 정적 화면을 제공해 소스 수정 시 재빌드가 필요하다. 개발용 Compose는 development target의 Vite·Watch를 사용한다.
- Front의 `/api`·`/actuator`는 404를 반환한다. Compose의 별도 프록시가 `/api`를 Back으로 라우팅한다. Front 내부 Nginx의 역할은 화면 제공이다.
- Back·AI·ML의 업무 API 연결, 모델 로드·예측, 기존 체선료 계산기 이관은 아직 없다.
- Compose에서 서비스 이름 `back`, `ai`, `ml`을 DNS 이름으로 사용한다. 예를 들어 AI가 ML에 접근하는 주소는 `http://ml:8000`이다. 컨테이너 안의 localhost는 그 컨테이너 자신이다.
- Compose 네트워크·프록시·DB·영속 볼륨은 구성했다. 다음은 업무 API·최적화·모델 연결과 Jenkins 빌드·배포다.

## Dockerfile 최초 검증 기록

2026-11-05, macOS arm64의 Docker Desktop에서 **Linux arm64 이미지**를 빌드·실행했다.

- Front·Back·AI·ML 이미지 4개 빌드 성공. Back 빌드 단계에서 Gradle 테스트·검사 통과.
- 네 서비스 모두 HTTP 상태 응답 200, Docker health 상태 `healthy`, 실행 UID 10001 확인.
- Front 기본 HTML·JS·CSS 제공, SPA 경로, 없는 정적 파일/API 경로의 404 확인.
- 별도 임시 Docker 네트워크에서 AI 컨테이너의 검사 명령으로 `ml:8000`, `back:8080`, `front:8080` 상태 API 접근 성공. DNS·HTTP 연결 확인이며 앱의 업무 호출 구현은 아니다.
- AI·ML 실행 이미지의 Python 3.12.13과 개발 도구 pytest·Ruff 미포함 확인. 모델 추론은 미구현이므로 검증하지 않았다.
- 검증용 컨테이너·네트워크는 종료·삭제했다. 빌드한 `port8282-*:local` 이미지와 빌드 캐시는 남겨 두었고 기존 볼륨 목록은 유지했다.
- 기반 이미지의 amd64·arm64 제공 여부를 확인했지만 **Linux amd64 서버·Windows 호스트에서의 실제 빌드·실행은 아직 검증하지 않았다.**
- 이 최초 검증 당시에는 DB·Compose를 검사하지 않았다. 이후 추가한 검증은 [Compose 개발 안내](compose.md)의 기록을 따른다. 업무 통합·Jenkins·운영 배포 복구는 아직 검증하지 않았다.

## 공식 참고 자료

- [Docker 다중 단계 빌드](https://docs.docker.com/build/building/multi-stage/): 빌드 도구와 실행 이미지 분리.
- [Docker build context와 .dockerignore](https://docs.docker.com/build/concepts/context/): 서비스별 복사 범위.
- [uv Docker 통합](https://docs.astral.sh/uv/guides/integration/docker/): lock 설치·다중 단계 구성.
