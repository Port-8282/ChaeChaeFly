# PORT 8282

**울산 터미널 선박 접안 스케줄링 프로젝트 · ChaeChaeFly**

어떤 배를 어느 선석에 먼저 배정해야 체선료를 줄일 수 있을까요?

PORT 8282는 SK에너지 울산 터미널을 대상으로 접안 스케줄을 비교하는 대시보드를 개발합니다. 선박 도착 일정과 부두 상황이 바뀌면 예상 체선료를 다시 계산하고, 담당자가 각 후보의 비용과 추천 근거를 보고 결정할 수 있도록 돕습니다.

**현재는 공통 개발 환경을 구성한 단계입니다.** Compose로 Proxy·Front·Back·AI·ML·PostgreSQL을 함께 실행하도록 구성했습니다. Vue 기본 화면, 상태 확인 API와 Back의 DB 연결을 제공하며 스케줄링·예측·보고서 같은 업무 기능은 아직 구현 전입니다. Jenkins CI 설정을 추가했으며 운영 배포는 보류합니다.

## 어떻게 동작하나요?

아래 흐름을 구현할 계획입니다. 선박·부두·기상 변화는 API에서 JSON으로 전달받는 것으로 가정합니다.

```text
선박 도착·부두 상태·기상 변화 수신
                ↓
접안 가능한 스케줄 탐색·예상 체선료 계산
                ↓
대시보드에서 후보·비용·추천 근거 비교
                ↓
담당자가 후보 선택·사유 입력
                ↓
선택한 일정과 사유를 담은 보고서 초안 작성
```

스케줄 탐색과 체선료 계산은 코드와 Tool이 수행합니다. ML은 하역시간을 예측하고, LLM은 계산 근거를 설명하거나 보고서 초안을 작성하는 데 사용합니다. 상태가 바뀌면 재계산한 결과를 대시보드에 반영합니다.

## 어디서 작업하나요?

하나의 저장소에서 담당 서비스별로 폴더를 나눠 작업합니다.

```text
ChaeChaeFly/
├── front/                   # 선박·부두 현황과 후보 비교 대시보드
├── back/                    # API, 상태 관리, DB 저장·조회
├── ai-data/
│   ├── ai-service/          # Agent, 스케줄 최적화, 체선료 계산 Tool
│   ├── ml-service/          # 하역시간 예측 API
│   └── training/            # 모델 학습·평가 위치 예약, 환경 구성 보류
├── contracts/               # 서비스 간 API·JSON 규격
├── data/                    # 공통 가상 데이터·검산 정답
├── infra/                   # 프록시, Jenkins, 배포 스크립트
├── tests/integration/       # 서비스 연결·전체 흐름 검증
├── docs/                    # 설계·개발·배포 안내
├── .github/                 # PR·Issue 작성 양식
├── compose.yaml             # 공통 서비스·네트워크·DB 볼륨
├── compose.dev.yaml         # 개발용 이미지·소스 변경 반영
├── Jenkinsfile              # 검사·테스트·이미지 빌드, 배포 제외
├── .env.example             # 환경변수 양식
├── .gitignore
├── CONTRIBUTING.md          # 브랜치·커밋·코드 작성 규칙
└── README.md
```

서비스별 Dockerfile과 공통·개발 Compose를 준비했습니다. 아직 비어 있는 기능·데이터 폴더는 `.gitkeep`으로 유지합니다. Jenkins CI 설치·연결 방법은 [CI 안내](docs/infra/ci.md)에 있습니다. 운영 서버용 설정은 아직 추가하지 않았습니다. 세부 경로는 [디렉토리 설계안](docs/directory-guide.md)을 참고하세요.

## 개발·배포 환경

| 항목 | 정한 방향 |
| --- | --- |
| 서비스 실행 | Docker Compose로 `proxy`, `front`, `back`, `ai`, `ml`, `db` 실행 |
| CI/CD | Jenkins를 앱과 별도 구성. Controller는 작업 관리, Agent는 검사·빌드 수행. 배포 보류 |
| Front | Vue 3.5.44·Vite 8.3.5 / Node.js 24.18.0·npm 11.16.0 |
| Back | Spring Boot 4.1.2 / JDK 21·Gradle Wrapper 9.8.2 |
| Python 환경 | AI 서비스·ML 추론을 독립 uv 프로젝트로 구성. Python 3.12.13 |
| AI와 ML 연결 | 별도 컨테이너로 실행하고 내부 HTTP·JSON으로 통신 |
| 모델 학습 | 현재 환경 구성은 보류. 학습 담당자의 검증 모델·전처리 정보를 ML 서비스에 전달 |
| DB | PostgreSQL 17.11·공식 bookworm 이미지. 앱 전용 계정 사용 |
| DB 보관 | 영속 볼륨에 저장하고 백업·복원은 별도 절차로 관리 |

Compose 접속 주소는 `http://127.0.0.1:8282`입니다. Front·Back 각각 내부 8080, AI·ML 각각 8000, DB 5432를 사용하고 호스트에는 Proxy 포트만 연결합니다. AI·ML의 최소 API는 FastAPI·Uvicorn으로 구성했습니다. 운영 서버·도메인은 아직 미정이며 전체 목표 구조는 [서비스·Jenkins 구성도](docs/infra/architecture.md)에 있습니다.

## 팀 공통 개발 환경 실행

Docker Desktop을 실행하고 Compose **2.32.0 이상**인지 확인합니다. 아래 명령은 **ChaeChaeFly 저장소 루트**에서 실행합니다. 이 방식에는 호스트의 Node.js·JDK·uv 설치가 필요하지 않습니다. 첫 빌드는 인터넷 연결이 필요합니다.

처음 한 번만 환경변수 파일을 준비합니다. 기존 `.env`가 있다면 덮어쓰지 말고 예시와 비교해 필요한 항목을 추가합니다.

```bash
# macOS·Linux
cp .env.example .env
```

Windows PowerShell에서는 `Copy-Item .env.example .env`를 사용합니다. 예시 비밀번호는 로컬 개발용이며 운영·공유 서버에서는 사용하지 않습니다.

```bash
docker compose version
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

- 기본 화면: `http://127.0.0.1:8282`
- Proxy 상태: `http://127.0.0.1:8282/health`
- Back·DB 상태: `http://127.0.0.1:8282/api/health`

Watch가 실행 중이면 Front·Python 소스 수정이 반영되고, Back 소스 수정은 재시작·재컴파일합니다. 라이브러리 설정·lock 변경은 해당 이미지를 다시 빌드합니다. 기존 로컬 `.venv`·`node_modules`는 컨테이너에 복사하지 않습니다.

종료는 Ctrl+C입니다. 컨테이너·네트워크까지 정리하려면 아래 명령을 사용합니다. DB 영속 볼륨은 유지됩니다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml down
```

설정 구조·컨테이너 안의 검사 명령·DB 유지 주의점은 [Compose 개발 안내](docs/infra/compose.md)에 있습니다. 실제 확인 범위도 해당 문서에 기록합니다. 개별 실행 이미지를 빌드하는 방법은 [Docker 안내](docs/infra/docker.md)를 참고합니다.

## 호스트에서 직접 개발하기 — 선택 사항

처음에는 [팀 GitHub Rules](docs/github-rules.md)를 읽고 담당 폴더의 README를 확인합니다. **Git은 설정 파일을 가져오며 설치 명령까지 실행하지는 않습니다.** 최신 설정을 자신의 작업 브랜치에 반영한 뒤 담당 서비스의 명령을 실행합니다.

아래는 Compose 대신 호스트에서 직접 개발할 때 사용하는 방법입니다. Node.js **24.18.0**·npm **11.16.0**, JDK **21**, uv **0.12.14 이상**을 준비합니다. 담당 서비스의 도구만 설치해도 됩니다. Node 버전 선택, JDK 설정과 Windows 명령은 [로컬 개발 안내](docs/infra/local-setup.md)에 있습니다. Gradle은 함께 제공한 Wrapper가 내려받으므로 전역 설치가 필요하지 않습니다.

아래 명령의 시작 위치는 모두 **ChaeChaeFly 저장소 루트**입니다.

```bash
# Front: lock 파일대로 라이브러리 설치
npm --prefix front ci

# Back: 의존성 준비·컴파일·상태 확인 테스트·JAR 생성
./back/gradlew -p back build

# AI·ML: 각 폴더에 독립 가상환경 구성
uv sync --locked --project ai-data/ai-service
uv sync --locked --project ai-data/ml-service
```

Windows PowerShell에서는 Back 명령을 `.\back\gradlew.bat -p back build`로 실행합니다. 첫 설치에는 인터넷 연결이 필요합니다.

## Front·Back 호스트 실행 — 선택 사항

저장소 루트에서 터미널 두 개를 열고 하나씩 실행합니다.

```bash
# 터미널 1 — Back
./back/gradlew -p back bootRun
```

```bash
# 터미널 2 — Front
npm --prefix front run dev
```

- 기본 화면: `http://127.0.0.1:5173`
- Back 상태: `http://127.0.0.1:8080/actuator/health`
- Front 개발 프록시를 거친 Back 상태: `http://127.0.0.1:5173/actuator/health`

상태 응답의 `status` 값은 `UP`입니다. **이 응답은 Back 프로세스 확인용이며 DB·AI·ML 연결이나 스케줄링 성공을 뜻하지 않습니다.** 종료는 각 터미널에서 Ctrl+C입니다. Windows에서는 `bootRun`도 `gradlew.bat`으로 실행합니다. 기본 주소로 실행할 때는 `.env` 파일이 필요하지 않습니다.

실행 설정·lock 파일은 Git에 공유하고 `node_modules/`, `.venv/`, `.gradle/`, `build/`, `dist/`는 각 컴퓨터에서 생성합니다. 실제 비밀값·업무자료·모델·DB 데이터는 Git에 올리지 않습니다. 모델 학습 환경은 보류했고 기존 체선료 계산기도 아직 이관 전입니다.

업무 API·데이터 형식은 `contracts/`에서 합의합니다. Jenkins CI 파일은 준비했지만 GitHub 연결과 필수 검사 적용은 별도 설정이 필요합니다. [CI 안내](docs/infra/ci.md)를 따라 인프라 담당자가 한 번 구성합니다.

## 함께 작업하는 방법

최신 `dev`에서 `feature/영역-작업명` 브랜치를 만들고, 완료한 작업은 `dev`로 PR을 올립니다. 통합 검증을 마친 뒤 같은 저장소의 `dev → main` PR로 반영합니다. 초기 공통 커밋과 `main`·`dev` 준비는 팀 개발을 시작하기 전에 진행합니다.

`main`·`dev`는 직접 push 없이 PR로 반영합니다. 작성자를 제외하고 **`main`은 4명 이상, `dev`는 1명 이상**의 승인을 받습니다. `main`에 병합하기 전에는 리뷰 대화도 모두 해결합니다. **GitHub 브랜치 보호와 Jenkins 필수 검사는 별도로 설정할 예정입니다.**

커밋과 PR 제목은 아래처럼 구분합니다. 경로별 제목 예시는 [PR 타이틀 규칙](docs/github-rules.md#pr-타이틀-규칙)에서 확인하세요.

| 구분 | 형식 | 예시 |
| --- | --- | --- |
| 커밋 메시지 | `type: [영역] 작업 내용` | `add: [infra] 초기 디렉토리 구조 구성` |
| PR 제목 | `[영역] 작업 내용` | `[infra] 초기 디렉토리 구조 구성` |

[PR 템플릿](.github/pull_request_template.md)이 기본 브랜치인 `main`에 반영되면 새 PR의 본문에 양식이 자동으로 표시됩니다. 제목과 본문 내용은 작성자가 채웁니다.

## 필요한 문서 찾기

| 확인할 내용 | 문서 |
| --- | --- |
| 로컬 환경·실행 설정 | [개발 환경 준비](docs/infra/local-setup.md) · [서버·포트·환경변수](docs/infra/specification.md) |
| 서비스 연결·배포 | [Compose 개발 안내](docs/infra/compose.md) · [Docker 사용 안내](docs/infra/docker.md) · [전체 구성도](docs/infra/architecture.md) · [배포·복구 계획](docs/infra/deployment.md) |
| API·데이터 형식 | [공통 규격 작성 기준](contracts/README.md) |
| 협업·리뷰 | [팀 GitHub Rules](docs/github-rules.md) · [상세 가이드](CONTRIBUTING.md) · [PR 양식](.github/pull_request_template.md) |
| 자동 검사·저장소 설정 | [Jenkins CI 구성](docs/infra/ci.md) · [브랜치 보호 설정](docs/infra/github-rules.md) |
| 테스트 | [통합 검증 항목](tests/integration/README.md) |
