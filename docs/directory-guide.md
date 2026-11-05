# ChaeChaeFly · 디렉토리 최종 설계안

> 기준: 2026-11-05 · 단일 레포 / Docker Compose / Jenkins / uv / AI·ML 별도 컨테이너
> 아래는 새 레포에 적용할 목표 구조다. 실행 파일·앱 코드가 모두 구현되어 있다는 뜻은 아니다.

**이 저장소 최상위에 front/, back/, ai-data/, infra/를 배치했다. Vue·Spring Boot·AI·ML 최소 실행 설정과 서비스별 Dockerfile을 작성했다. 공통·개발용 Compose와 프록시·PostgreSQL 설정도 작성했다. Jenkins CI 구성 파일을 추가했다. 서버 배포용 compose.prod.yaml과 CD는 구현 전이며 학습 환경은 보류한다.**

## 1. 최종 디렉토리

~~~text
ChaeChaeFly/
├── README.md                         # 프로젝트 소개·진행 상태·실행 안내
├── CONTRIBUTING.md                   # 브랜치·커밋·코드·API·리뷰 규칙
├── .github/
│   ├── pull_request_template.md       # PR 작성 양식
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md             # 버그 보고 양식
│       └── feature_request.md        # 기능·작업 요청 양식
├── .gitattributes                    # Linux 셸 스크립트의 LF 줄바꿈 유지
├── .gitignore                        # 비밀값·가상환경·생성 데이터 제외
├── .env.example                      # 환경변수 양식, 실제 비밀값 제외
├── compose.yaml                      # 공통 서비스·네트워크·볼륨 정의
├── compose.dev.yaml                  # 로컬 개발용 빌드·소스 연결
├── compose.prod.yaml                 # 서버용 고정 이미지·운영 설정
├── Jenkinsfile                       # CI 검사·테스트·빌드, 배포 없음
│
├── front/                            # Front 컨테이너
│   ├── README.md
│   ├── .nvmrc / .node-version       # Node.js 버전
│   ├── package.json / package-lock.json
│   ├── nginx.conf                  # 컨테이너의 정적 화면 제공
│   ├── vite.config.js / index.html
│   ├── .env.example                 # 개발 프록시 주소 양식
│   ├── src/                          # 대시보드·상태 표시·후보 선택
│   ├── public/                       # 공개 정적 파일
│   ├── tests/                        # 화면·컴포넌트 테스트
│   ├── Dockerfile
│   └── .dockerignore
│
├── back/                             # Back 컨테이너
│   ├── README.md
│   ├── .java-version                # JDK 21
│   ├── build.gradle / settings.gradle / gradle.lockfile
│   ├── gradlew / gradlew.bat
│   ├── gradle/wrapper/              # Wrapper JAR·다운로드 버전·checksum
│   ├── src/main/                    # Spring 앱·설정, 이후 API·DB 구현
│   ├── src/test/                    # 상태 확인 HTTP 테스트
│   ├── tests/                        # 초기 예약 폴더, Java 테스트는 src/test 사용
│   ├── db/
│   │   └── migrations/               # DB 구조 변경 이력
│   ├── Dockerfile
│   └── .dockerignore
│
├── ai-data/
│   ├── README.md
│   ├── ai-service/                   # AI 컨테이너
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── port8282_ai/
│   │   │   │   ├── api/              # Back에서 호출하는 API
│   │   │   │   ├── workflows/        # 정해진 계산·최적화 실행 흐름
│   │   │   │   ├── agents/           # 근거 설명·선택 결과 보고서
│   │   │   │   ├── optimization/     # 접안 후보 탐색·최적화 알고리즘
│   │   │   │   ├── tools/            # 제약·시뮬레이션·계산 Tool 연결
│   │   │   │   └── clients/          # ML·LLM API 호출
│   │   │   └── port8282_demurrage/   # 기존 체선료 계산 패키지
│   │   ├── tests/                    # 계산 규칙·최적화·API 테스트
│   │   ├── examples/                 # AI·계산 Tool 최소 실행 예제
│   │   ├── schemas/                  # 계산 Tool 전용 입력·출력 스키마
│   │   ├── validation/               # 오프라인 정답 비교·검산 코드
│   │   ├── .python-version       # Python 3.12.13
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── Dockerfile             # uv 잠금 설치·최소 API 실행
│   │   └── .dockerignore
│   │
│   ├── ml-service/                   # ML 추론 컨테이너
│   │   ├── README.md
│   │   ├── src/
│   │   │   └── port8282_ml/
│   │   │       ├── api/              # AI에서 호출하는 예측 API
│   │   │       ├── preprocessing/    # 추론 입력 전처리
│   │   │       └── inference/        # 모델 로드·예측·버전 확인
│   │   ├── tests/                    # 전처리·추론·API 테스트
│   │   ├── .python-version       # Python 3.12.13
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── Dockerfile             # uv 잠금 설치·최소 API 실행
│   │   └── .dockerignore
│   │
│   └── training/                     # 별도 학습·평가 위치, 환경 구성 보류
│       ├── README.md
│       ├── src/                      # 데이터 준비·학습·평가 코드
│       ├── notebooks/                # 탐색·실험 노트북
│       └── tests/                    # 학습 데이터·전처리 검증 위치 예약
│
├── contracts/                        # 서비스 간 통신 규격 원본
│   ├── README.md
│   ├── api/                          # HTTP API 명세
│   ├── schemas/                      # 공통 이벤트·메시지 JSON Schema
│   └── examples/                     # 규격 설명용 작은 JSON 예시
│
├── data/                             # 공유 가능한 가상 테스트 데이터
│   ├── mock/
│   │   ├── README.md
│   │   ├── master/                   # 가상 선박·부두·상품·계약 정보
│   │   └── scenarios/                # 시작 상태·순차 JSON 이벤트
│   └── expected/                     # 시나리오별 검산 정답
│
├── infra/                            # 인프라 담당 영역
│   ├── README.md
│   ├── proxy/nginx.conf             # 화면·API·개발 HMR 연결
│   ├── db/init/10-app-user.sh         # 최초 DB 생성 때 앱 계정·권한 준비
│   ├── jenkins/                      # Controller·Agent 설치·권한 설정
│   └── scripts/
│       ├── README.md
│       ├── ci.py                     # CI 검사·결과 기록·전용 자원 정리
│       ├── deploy.sh                 # 릴리스 명세로 서버 배포
│       ├── smoke-test.sh             # 준비 상태·대표 API 기본 확인
│       ├── rollback.sh               # 이전 앱 버전 복구·재확인
│       ├── backup-db.sh              # 별도 저장소로 DB 백업
│       └── restore-db.sh             # 별도 절차로 DB 복원
│
├── tests/
│   └── integration/                  # Front·Back·AI·ML·DB 연결 검증
│       └── README.md
│
└── docs/
    ├── directory-guide.md            # 이 디렉토리 설계안
    ├── architecture-review.md        # 서비스·배포 구조 검토 기록
    ├── infra/
    │   ├── local-setup.md            # 로컬 개발·통합 실행 안내
    │   ├── docker.md                 # 서비스별 이미지 빌드·실행·검증 범위
    │   ├── compose.md                # 팀 공통 Docker 개발 환경·Watch 사용법
    │   ├── specification.md          # 서버·포트·환경변수·버전 명세
    │   ├── architecture.md           # 서비스·Jenkins 구성도
    │   ├── github-rules.md           # main·dev 보호 규칙 적용 안내
    │   └── deployment.md             # 배포·검증·복구·백업 절차
    └── api/                          # 사용 설명, contracts 원본 참조
~~~

Front는 Vue·npm, Back은 Spring Boot·Gradle 초기 프로젝트를 구성했다. 의존성 설정·lock 파일·Wrapper를 서비스별로 공유한다. AI·ML의 최상위 Python 패키지는 초기화했으며 하위 패키지에는 __init__.py를 추가한다. Back Java 테스트는 src/test/java, 설정은 src/main/resources를 사용하며 migration 도구와 경로는 DB 도입 시 맞춘다.

## 2. 폴더와 실행 서비스

front → front, back → back, ai-service → ai, ml-service → ml 컨테이너로 실행한다. infra/proxy는 proxy의 설정이며 DB 제품의 이미지와 영속 볼륨으로 db를 실행한다. **상시 앱 서비스는 6개**다. 별도 DB 앱 소스 폴더는 필요하지 않다.

Jenkins는 별도 관리하고 training은 상시 서비스가 아니다. 현재 AI·ML만 각각 독립된 uv 프로젝트로 구성하며 ai-data 루트에는 공통 pyproject.toml을 추가하지 않는다. training 환경 초기화는 보류하고 필요할 때 별도로 구성한다. 학습·추론의 전처리는 같은 정의 또는 함께 저장한 전처리 산출물을 재사용하여 일치 여부를 검증한다.

## 3. Docker·Compose 구성 원칙

- compose.yaml: 공통 연결·내부 네트워크·DB 볼륨·준비 상태. 개발용 소스 마운트·디버그 포트는 넣지 않는다.
- compose.dev.yaml: development 이미지 빌드, Compose Watch 소스 동기화·자동 반영, Gradle 캐시. 앱 소스 전체를 bind mount하지 않아 호스트 .venv·node_modules가 섞이지 않는다.
- compose.prod.yaml: Registry의 고정 이미지 digest, 운영 환경·자원·공개 포트. 앱 서버는 이미지를 받아 실행한다.

현재 로컬 개발 명령은 docker compose -f compose.yaml -f compose.dev.yaml up --build --watch이다. 서버는 공통 파일과 compose.prod.yaml을 조합한다. **공통·개발용 Compose는 작성했으며 운영용 compose.prod.yaml은 아직 없다. [Compose 개발 안내](infra/compose.md)를 따른다.** CI에서 각 조합의 docker compose config 결과를 확인한다. Compose는 파일을 순서대로 병합하므로 개발 설정과 운영 설정을 분리한다. [Docker Compose 병합 문서](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)

이미지 빌드 context는 각각 front/, back/, ai-data/ai-service/, ai-data/ml-service/로 정한다. 각 폴더의 Dockerfile·.dockerignore가 적용된다. 이 레포는 루트 대신 각 서비스의 .dockerignore를 사용한다. [Docker build context 문서](https://docs.docker.com/build/concepts/context/)

루트 contracts와 data는 레포 전체를 체크아웃한 CI의 규격·통합 검증에서 사용한다. 앱이 실행 중 루트 폴더를 직접 읽도록 만들지 않는다. 공통 규격을 실행 이미지에 포함해야 한다면 명시적인 생성·패키징 단계를 추가한다. 서비스 Dockerfile에서 COPY ../contracts 같은 경로를 쓰지 않는다.

모델은 ML 출시 작업이 위치·SHA256을 확인하고 **ai-data/ml-service/build-assets/**에 임시 준비하여 이미지에 포함한다. 이 경로는 Git에서 제외하며 모델 저장소가 원본이다. 실행 중 모델 파일을 덮어쓰지 않는다.

## 4. 중복 관리 방지

- contracts/api: API 규격 원본. docs/api는 사용 방법과 원본 링크를 담는다.
- contracts/schemas: 공통 JSON 규격. 루트 data/schemas는 별도로 만들지 않는다.
- ai-service/schemas: 기존 계산 Python Tool 전용 스키마. 같은 규격을 contracts에 복제하지 않는다. 외부 API로 그대로 공개할 경우 소유 위치를 하나로 정한다.
- data/mock: 전체 시연·통합 테스트 입력. contracts/examples는 규격 설명용 최소 예시.
- data/expected: 전체 시나리오의 기대 결과. 비교할 때만 사용하며 ML 입력 특징에 넣지 않는다.
- ai-service/examples: 계산기·AI의 작은 실행 예제. 전체 시연 데이터의 복사본을 쌓지 않는다.
- 서비스별 tests: 단위 테스트. 루트 tests/integration: 여러 서비스 연결과 전체 흐름 검증.

## 5. 기존 체선료 계산기 이관

현재 기준 원본은 기존 작업 공간의 demurrage_tool이다.

- src/port8282_demurrage → ai-data/ai-service/src/port8282_demurrage.
- 테스트·예제·스키마·검산 코드 → AI 서비스의 tests, examples, schemas, validation.
- Python 패키지 설정·CLI 진입점 → AI 서비스 pyproject.toml에 통합.

파일 경로를 조정하고 이관 전후 결과가 같은지 확인한 뒤 새 위치를 단일 개발 원본으로 삼는다. **현재 원본 이동·복사는 하지 않았다.** 과거 SOF를 사용하는 검산 코드는 validation에 두며 예상 스케줄 계산의 운영 입력과 분리한다.

## 6. 첫 커밋

지금은 디렉토리, 폴더별 README, CONTRIBUTING.md, .github의 PR·Issue 템플릿, .gitignore, 비밀값 없는 .env.example, 설계 문서와 확정한 예시 JSON부터 올린다. 협업은 [GitHub Rules](../CONTRIBUTING.md)의 feature → dev → main 전략을 따른다. 템플릿은 기본 브랜치에 반영한다. 새 빈 폴더에는 README 또는 .gitkeep을 두어 Git에 남긴다. .gitkeep은 Git의 특별한 기능이 아니라 빈 폴더를 남기기 위한 관례적인 파일명이다.

서비스별 Dockerfile과 공통·개발용 Compose는 작성했다. Jenkinsfile과 CI 스크립트는 작성했다. 운영용 Compose·운영 스크립트는 실제 내용을 구현할 때 추가한다. 빈 실행 파일을 만들고 동작하는 설정처럼 취급하지 않는다. uv.lock은 의존성을 정의한 후 uv로 생성해 커밋한다. [uv 프로젝트·lock 파일 문서](https://docs.astral.sh/uv/concepts/projects/layout/)

.env, .venv, 원본 업무자료, DB 데이터·백업, 모델 바이너리, Jenkins 상태는 Git에 올리지 않는다. 현재 제공된 .gitignore를 새 레포에 포함한다.

## 7. 담당 범위·변경 검증

인프라 담당자는 **루트 Compose 3개와 Jenkinsfile, infra, docs/infra**를 관리한다. 서비스별 Dockerfile은 해당 개발자와 실행 명령·포트·준비 상태를 맞춰 작성한다. contracts와 통합 테스트는 공동으로 합의한다.

Front 변경은 화면/API, Back 변경은 이벤트·DB·AI, AI 변경은 규칙·최적화·ML 호환을 검사한다. ML 변경은 평가·추론·기존 AI 호환을 확인한다. 공통 API나 배포 설정 변경은 관련 서비스와 전체 통합을 검사한다. 학습 코드 변경만으로 모델을 자동 출시하지 않는다.

현재 Jenkins CI는 검사 → 이미지 빌드·테스트 → 기본 응답 확인 → 결과 보관까지다. 향후 CD는 Registry → 전체 릴리스 기록 → 공통 배포 잠금 → 대상 갱신 → 준비 상태·통합 확인으로 연결할 계획이다. 모델 버전·DB·복구 규칙은 [아키텍처 검토](architecture-review.md)를 따른다.

Front는 Node.js 24.18.0·npm 11.16.0·Vue 3.5.44·Vite 8.3.5, Back은 JDK 21·Spring Boot 4.1.2·Gradle 9.8.2로 구성했다. AI·ML은 Python 3.12.13의 독립 uv 프로젝트다. AI·ML의 최소 API는 FastAPI·Uvicorn으로 구성했다. DB는 PostgreSQL 17.11로 확정했다. 서버·Registry·운영 외부 포트는 미정이다. 실행 명령은 [로컬 개발 안내](infra/local-setup.md)를 따른다.
