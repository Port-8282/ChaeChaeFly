# PORT 8282

**울산 터미널 선박 접안 스케줄링 프로젝트 · ChaeChaeFly**

어떤 배를 어느 선석에 먼저 배정해야 체선료를 줄일 수 있을까요?

PORT 8282는 SK에너지 울산 터미널을 대상으로 접안 스케줄을 비교하는 대시보드를 개발합니다. 선박 도착 일정과 부두 상황이 바뀌면 예상 체선료를 다시 계산하고, 담당자가 각 후보의 비용과 추천 근거를 보고 결정할 수 있도록 돕습니다.

**현재는 개발 준비 단계입니다.** 폴더 구조, 협업 규칙, PR·Issue 템플릿과 인프라 설계 문서를 마련했습니다. 서비스 코드와 Docker Compose, Jenkins 설정은 구현 전이므로 아직 앱을 실행할 수 없습니다.

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
│   └── training/            # 모델 학습·평가
├── contracts/               # 서비스 간 API·JSON 규격
├── data/                    # 공통 가상 데이터·검산 정답
├── infra/                   # 프록시, Jenkins, 배포 스크립트
├── tests/integration/       # 서비스 연결·전체 흐름 검증
├── docs/                    # 설계·개발·배포 안내
├── .github/                 # PR·Issue 작성 양식
├── .env.example             # 환경변수 양식
├── .gitignore
├── CONTRIBUTING.md          # 브랜치·커밋·코드 작성 규칙
└── README.md
```

빈 소스·데이터 폴더는 `.gitkeep`으로 유지하고 있습니다. 서비스별 `.dockerignore`는 준비했으며, 실행 코드와 설정 파일은 개발하면서 추가합니다. 세부 경로는 [디렉토리 설계안](docs/directory-guide.md)을 참고하세요.

## 개발·배포 환경

| 항목 | 정한 방향 |
| --- | --- |
| 서비스 실행 | Docker Compose로 `proxy`, `front`, `back`, `ai`, `ml`, `db` 실행 |
| CI/CD | Jenkins를 앱과 별도 구성. Controller는 작업 관리, Agent는 검사·빌드·배포 수행 |
| Python 환경 | AI 서비스·ML 추론·학습을 각각 독립된 uv 프로젝트로 관리 |
| AI와 ML 연결 | 별도 컨테이너로 실행하고 내부 HTTP·JSON으로 통신 |
| 모델 학습 | 별도 작업으로 수행하고 검증된 모델을 ML 추론 서비스에 배포 |
| DB 보관 | 영속 볼륨에 저장하고 백업·복원은 별도 절차로 관리 |

Front·Back 프레임워크, DB 제품, 서버와 포트는 팀에서 확정할 예정입니다. 전체 연결과 배포 흐름은 [서비스·Jenkins 구성도](docs/infra/architecture.md)에 정리했습니다.

## 개발을 시작하려면

1. [협업 규칙](CONTRIBUTING.md)을 읽고 담당 폴더의 `README.md`를 확인합니다.
2. 함께 연결할 서비스의 API·데이터 형식을 `contracts/`에서 맞추고, 실행 환경을 정합니다.
3. 서비스 코드와 의존성을 구성한 뒤 Dockerfile·Compose·Jenkins를 연결합니다. Python은 각 프로젝트의 `pyproject.toml`과 실제로 생성한 `uv.lock`을 함께 관리합니다.

실행 명령은 서비스 구현 후 [로컬 개발 안내](docs/infra/local-setup.md)에 추가합니다. 기존 체선료 계산기는 `ai-data/ai-service/src/port8282_demurrage/`로 이관할 예정이며, 코드·테스트·예제·스키마를 함께 옮겨 결과를 확인합니다.

`.env.example`에는 변수 이름 초안만 있습니다. 실제 `.env`, `.venv`, 업무 원본자료, 모델 파일, DB 데이터·백업은 Git에 올리지 않습니다.

## 함께 작업하는 방법

최신 `dev`에서 `feature/영역-작업명` 브랜치를 만들고, 완료한 작업은 `dev`로 PR을 올립니다. 통합 검증을 마친 뒤 같은 저장소의 `dev → main` PR로 반영합니다. 초기 공통 커밋과 `main`·`dev` 준비는 팀 개발을 시작하기 전에 진행합니다.

`main`·`dev`는 직접 push 없이 PR과 작성자 외 1명 이상의 승인을 거칩니다. `main`에 병합하기 전에는 리뷰 대화도 모두 해결합니다. **GitHub 브랜치 보호와 Jenkins 필수 검사는 별도로 설정할 예정입니다.**

커밋과 PR 제목은 `type: [영역] 작업 내용`으로 작성합니다.

```text
add: [infra] 초기 디렉토리 구조와 협업 템플릿 구성
```

[PR 템플릿](.github/pull_request_template.md)이 기본 브랜치인 `main`에 반영되면 새 PR의 본문에 양식이 자동으로 표시됩니다. 제목과 본문 내용은 작성자가 채웁니다.

## 필요한 문서 찾기

| 확인할 내용 | 문서 |
| --- | --- |
| 로컬 환경·실행 설정 | [개발 환경 준비](docs/infra/local-setup.md) · [서버·포트·환경변수](docs/infra/specification.md) |
| 서비스 연결·배포 | [전체 구성도](docs/infra/architecture.md) · [배포·복구 계획](docs/infra/deployment.md) |
| API·데이터 형식 | [공통 규격 작성 기준](contracts/README.md) |
| 협업·리뷰 | [컨벤션](CONTRIBUTING.md) · [PR 양식](.github/pull_request_template.md) · [브랜치 보호 설정](docs/infra/github-rules.md) |
| 테스트 | [통합 검증 항목](tests/integration/README.md) |
