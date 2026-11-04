# PORT 8282 협업 가이드

작업을 시작하고, 변경 내용을 공유하고, 리뷰를 거쳐 합치는 방법을 정리했습니다. Front·Back·AI·ML이 하나의 저장소에서 작업하므로 다른 파트에 영향을 주는 변경은 PR에 함께 적습니다.

브랜치·커밋·PR 규칙만 빠르게 확인하려면 [팀 GitHub Rules](docs/github-rules.md)를 참고하세요.

**현재는 규칙과 템플릿을 준비한 단계입니다.** GitHub 브랜치 보호와 Jenkins 필수 검사는 아직 설정하지 않았습니다. 프로젝트 구조는 [README](README.md), 세부 경로는 [디렉토리 설계안](docs/directory-guide.md)에서 확인할 수 있습니다.

## 작업은 feature에서 시작합니다

최신 `dev`에서 작업 브랜치를 만들고, 완료한 기능을 `dev`에 모아 검증합니다. 운영에 반영할 변경은 `dev → main` PR로 올립니다.

```text
최신 dev에서 feature/영역-업무내용 생성
                ↓
개발·테스트 → dev로 PR → 리뷰 후 병합
                ↓
통합 검증 → main으로 PR → 리뷰 후 병합
```

| 브랜치 | 역할 | 작업·PR 흐름 |
| --- | --- | --- |
| `feature/*` | 개인 기능 개발 | 작업을 마치면 `dev`로 PR 제출 |
| `dev` | 기능을 모아 통합 검증 | 기능 PR, `main → dev` 동기화 PR |
| `main` | 운영에 반영할 검증된 코드 | **같은 저장소의 `dev`에서 보낸 PR만** |

`main`과 `dev`에는 **직접 push, force push, 브랜치 삭제를 허용하지 않습니다.** 작성자를 제외하고 **`main` 대상 PR은 4명 이상, `dev` 대상 PR은 1명 이상**의 승인(Approve)을 받습니다. 관리자·자동화 계정도 이 규칙을 우회하지 않도록 설정합니다.

`main`에 병합하기 전에는 리뷰 대화를 모두 해결(Resolve)해야 합니다. `dev`도 리뷰 지적사항을 처리한 뒤 병합하며, 대화 해결을 GitHub에서 강제하는 설정은 권장합니다.

작업 브랜치 이름은 `feature/영역-업무내용`으로 짓습니다. 영문 소문자·숫자·하이픈을 사용하고, 이름만 봐도 작업을 알 수 있게 적습니다.

```text
feature/front-dashboard
feature/ai-demurrage
feature/infra-compose
```

- 한 브랜치는 한 사람이 하나의 목적을 맡는 것을 기본으로 합니다.
- 기능·테스트·문서를 확인한 뒤 `dev`로 PR을 올립니다. `feature`에서 `main`으로 직접 PR을 보내지 않습니다.
- 완료된 `feature`는 `dev`에 병합한 뒤 삭제합니다. `main`과 `dev`는 계속 유지합니다.
- 브랜치명에 이슈 번호를 넣을 필요는 없습니다. 관련 GitHub Issue가 있으면 PR 본문에 연결합니다.
- 다른 사람의 변경이나 공유 브랜치의 이력을 임의로 삭제하거나 다시 쓰지 않습니다.

### 병합 방식은 다음을 제안합니다

| 경로 | 병합 방식 | 이유 |
| --- | --- | --- |
| `feature → dev` | Squash merge | 한 작업을 한 커밋으로 정리 |
| `dev → main` | Create a merge commit | 계속 사용하는 브랜치의 이력 보존 |
| `main → dev` | Create a merge commit | 배포 PR 병합 후 두 브랜치의 기준 동기화 |

Squash merge 시 최종 커밋 제목은 `type: [영역] 작업 내용`으로 맞춥니다. PR 제목은 `[영역] 작업 내용`을 유지합니다.

`main → dev` 동기화 PR도 `dev`의 승인 규칙을 따릅니다. 이 방식을 쓰려면 Merge commit과 Squash를 모두 허용하고, Merge commit과 충돌하는 선형 이력 강제 설정은 켜지 않습니다. 계속 사용하는 브랜치를 반복해서 Squash하면 다음 PR에 이전 커밋이 다시 표시될 수 있습니다. [GitHub 병합 방식 안내](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)

## 커밋 메시지 작성 기준

**`type: [영역] 작업 내용`**

```text
add: [infra] 초기 디렉토리 구조 생성
update: [front] 대기 선박 필터 추가
bugfix: [ai] 기상 제외 시간 중복 차감 수정
test: [ai] 주말 산입 경계 테스트 추가
script: [ml] 추론 의존성과 uv.lock 갱신
docs: [docs] GitHub 협업 규칙 정리
```

영역은 `front`, `back`, `ai`, `ml`, `training`, `infra`, `api`, `data`, `docs`, `repo` 중에서 고릅니다. 외부 티켓 키는 넣지 않습니다. GitHub가 자동으로 만드는 Merge commit 제목은 기본 형식을 그대로 사용해도 됩니다.

| 타입 | 사용할 때 |
| --- | --- |
| `update` | 기존 파일에 새로운 기능을 추가할 때 |
| `add` | 새 파일을 만들거나 초기 설정을 할 때 |
| `bugfix` | 재현되는 버그를 고칠 때 |
| `refactor` | 외부 동작은 유지하면서 코드 구조를 개선할 때 |
| `fix` | 버그 수정·구조 개선 외의 작은 코드·설정 수정을 할 때 |
| `move` | 파일·폴더를 옮기거나 이름을 바꿀 때 |
| `del` | 기능이나 파일을 삭제할 때 |
| `test` | 테스트 코드를 작성하거나 수정할 때 |
| `style` | CSS·화면 스타일을 수정할 때 |
| `gitfix` | `.gitignore` 규칙을 수정할 때 |
| `script` | `package.json`, `pyproject.toml`, lock 파일, 빌드·배포 스크립트를 변경할 때 |
| `docs` | 문서를 작성하거나 수정할 때 |
| `etc` | 기존 타입에 해당하지 않는 기타 작업을 할 때 |

문서만 작성·수정하는 작업은 `docs`를 사용합니다. 기존 타입으로 분류하기 어려운 기타 작업은 `etc`를 사용하고 제목에 구체적인 작업 내용을 적습니다. 여러 타입이 해당하면 변경의 주된 목적을 기준으로 고릅니다.

커밋은 기능이나 수정 목적별로 작게 나눕니다. 관련 코드·테스트·문서는 함께 이해하고 되돌릴 수 있는 단위로 묶어도 됩니다. 파일마다 따로 커밋할 필요는 없습니다.

## PR 제목 작성 기준

PR 제목은 **`[영역] 작업 내용`**으로 씁니다. 타입은 생략하고 PR 전체 변경을 한 줄로 요약합니다. 영역은 영문 소문자로 쓰고 대괄호 뒤는 한 칸 띄웁니다. `수정`, `최종`만 적기보다 바뀐 기능이나 파일을 구체적으로 적습니다.

예를 들어 문서 수정 커밋은 `docs: [docs] GitHub 협업 규칙 정리`, PR 제목은 `[docs] GitHub 협업 규칙 정리`로 작성합니다. 커밋 메시지의 13개 타입은 그대로 사용합니다.

여러 서비스의 변경을 묶는 배포 준비·이력 동기화 PR은 영역을 `repo`로 표시합니다. API 호환을 깨는 변경은 제목에 `호환성 변경`을 표시합니다. 경로별 예시는 [팀 PR 타이틀 규칙](docs/github-rules.md#pr-타이틀-규칙)을 참고하세요.

## PR에는 변경 이유와 확인한 결과를 적습니다

[PR 템플릿](.github/pull_request_template.md)에 따라 아래 내용을 채웁니다. 아직 작업 중이라면 Draft PR로 올립니다.

1. **작업 내용:** 어떤 문제를 해결했고, 변경 후 동작이 어떻게 달라지는지 적습니다.
2. **변경 사항:** 주요 파일·기능과 영향을 받는 파트를 적습니다. 관련 Issue가 없으면 `없음`으로 표시합니다.
3. **검증 결과:** 실행한 명령과 실제 결과, 스크린샷·API 응답·로그 등 근거를 남깁니다. 계산 변경은 입력·규칙·정답 비교 결과를, 모델 변경은 평가 결과와 모델 버전을 함께 적습니다. 코드만 읽어 확인한 내용과 실행한 결과를 구분합니다.
4. **배포·호환성 영향:** API·환경변수·DB·모델 변경이 다른 서비스에 미치는 영향을 적습니다. API 호환을 깨는 변경은 제목에도 표시하고, 소비 서비스의 수정·전환 방법을 설명합니다.
5. **참고·리뷰 요청:** 미완료 작업이나 제한사항, 집중해서 봐 줬으면 하는 부분을 적습니다.

제출 전에는 **괄호 안 도움말·예시값·안내 주석을 지우고 실제 내용으로 바꿉니다.** 미해당 항목은 `해당 없음`, 실행하지 않은 검사는 `미실행: 이유`로 적습니다.

버그·요청사항은 GitHub Issue에 구체적으로 남깁니다. 버그는 먼저 [버그 템플릿](.github/ISSUE_TEMPLATE/bug_report.md)에 재현 방법과 기대·실제 결과를 적고, 이슈 링크를 Slack·ZEP 등 팀 채널에 공유합니다. 기능이나 인프라 작업은 [요청 템플릿](.github/ISSUE_TEMPLATE/feature_request.md)을 사용합니다. 관련 PR에는 해당 이슈를 연결합니다.

### 템플릿이 적용되는 방식

```text
.github/
├── pull_request_template.md
└── ISSUE_TEMPLATE/
    ├── bug_report.md
    └── feature_request.md
```

위 파일을 기본 브랜치인 `main`에 반영하면 새 PR·Issue 작성 시 양식을 사용할 수 있습니다. PR 제목은 직접 작성하며, 이미 작성한 PR 본문은 자동으로 바뀌지 않습니다. [PR 템플릿 안내](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository) · [Issue 템플릿 안내](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)

템플릿은 작성 양식입니다. 제목·본문 작성 규칙을 강제하는 자동화는 아직 없으며, 체크박스만으로 승인이나 출발 브랜치를 제한할 수도 없습니다. 이런 제한은 GitHub 보호 규칙과 Jenkins 검사로 별도 설정합니다.

## 파일과 코드 이름을 맞춥니다

| 대상 | 형식 | 예시 |
| --- | --- | --- |
| 공통 폴더·문서·스크립트 | 영문 소문자·하이픈 | `ai-service`, `local-setup.md`, `smoke-test.sh` |
| Python 패키지·모듈·함수·변수 | snake_case | `port8282_ai`, `calculate_demurrage` |
| 클래스 | PascalCase | `DemurrageCalculator` |
| JavaScript·TypeScript 함수·변수 | camelCase | `selectedCandidate` |
| 상수·환경변수 | UPPER_SNAKE_CASE | `ML_BASE_URL` |

프레임워크 예약 이름과 클래스·컴포넌트 파일명은 해당 기술 스택의 관례를 따릅니다. 코드·식별자는 영어, 문서·업무 주석은 한국어를 기본으로 합니다. 주석에는 코드가 하는 일을 반복하기보다 작성 이유나 계약 규칙의 근거를 남깁니다.

인코딩은 UTF-8, 줄바꿈은 LF를 사용합니다. Python 들여쓰기는 공백 4칸을 제안합니다. Front·Back 포맷터·린터·줄 길이는 기술 스택을 확정한 뒤 설정 파일로 공유합니다. 개인 취향으로 파일 전체 형식을 바꾸지 않습니다.

## API와 데이터는 함께 바꿉니다

규격 원본은 `contracts/`에서 관리합니다. 필드 이름·자료형·단위를 바꾸면 규격, 예시, 소비 서비스와 관련 검증을 같은 PR에서 수정합니다. 상세 경로·메서드·오류 형식은 API 담당자와 합의할 예정입니다.

- **이름:** JSON 필드는 snake_case를 기본으로 합니다. Front 내부에서 camelCase가 필요하면 API 경계에서 변환합니다. 외부 API 경로는 소문자 명사·하이픈을 기본안으로 하고 `contracts/api/`에서 정합니다.
- **기존 데이터:** 목업·계산기의 컬럼 의미와 형식을 먼저 확인합니다. `early_start_if_work`의 Y/N, 대문자 enum, 숫자 자료형을 이름 규칙에 맞추려고 임의로 바꾸지 않습니다.
- **날짜·시간:** 시간대를 포함한 ISO 8601로 주고받습니다. 예: `2026-11-06T09:00:00+09:00`. 울산 시각은 `Asia/Seoul`로 표시하고, 주말·휴무일 산입은 계약·계산 명세의 현지 시간대를 따릅니다. 저장 형식과 계약상 날짜 판단 기준을 구분합니다.
- **단위·금액:** 새 필드는 `waiting_min`, `cargo_mt`, `demurrage_usd`처럼 이름이나 명세에 단위를 적습니다. 기존 단위는 임의로 바꾸지 않습니다. 계산 정밀도·반올림 시점은 계산기 규칙을 따르고, 새 금액 필드의 JSON 숫자·문자열 형식은 `contracts/`에서 정합니다.
- **오류:** 실패·미계산·결측을 비용 `0`이나 정상적인 빈 결과로 바꾸지 않습니다. 상태 코드, 오류 코드, 설명, 요청 추적 ID를 함께 정합니다.
- **추적:** 이벤트는 `event_id`, 입력 상태는 `state_version`, 계산 한 건은 `calculation_id`로 식별합니다. 결과에는 적용한 모델·규칙 버전을 남깁니다.

**`effective_start_local`은 NOR 통지 시점과 같은 뜻으로 쓰지 않습니다.** 용어와 필드의 의미는 [공통 규격 작성 기준](contracts/README.md)에 맞춥니다.

## 실행 환경과 비밀정보를 관리합니다

AI 서비스·ML 추론·학습은 각각 uv 프로젝트로 관리합니다. 의존성을 추가하거나 변경하면 `pyproject.toml`과 실제 생성한 `uv.lock`을 함께 커밋합니다. 빈 lock 파일은 만들지 않습니다.

새 환경변수는 `.env.example`과 인프라 명세에 이름·용도·사용 서비스를 적습니다. 실행할 때는 각 서비스에 필요한 값만 전달합니다.

| Git에 올릴 것 | Git에 올리지 않을 것 |
| --- | --- |
| 의존성 정의·lock 파일, 환경변수 양식 | 실제 `.env`, 로컬 `.venv`, 비밀번호·API 키·인증서 비밀키 |
| 공유 가능한 가상 데이터·검증 코드·모델 버전 정보 | 실제 원본 업무자료, 큰 모델 파일, DB 데이터·백업, Jenkins 상태 |

업무자료와 모델 파일은 별도 저장소에서 관리합니다. 로그에도 비밀값이나 전체 원본 데이터를 남기지 않습니다.

## 변경한 내용에 맞춰 검증합니다

| 변경 내용 | 확인할 것 |
| --- | --- |
| 기능·버그 수정 | 관련 동작을 실행하고 PR에 명령·결과 기록 |
| 계약 규칙·체선료 계산 | 입력·규칙, 경계·예외 조건, 수기 정답과의 비교 |
| API | 요청·응답 변경 후 관련 서비스 간 호환 |
| 배포 설정 | 개발용·운영용 Compose 조합 |
| 모델 출시 | artifact 위치·해시, 모델·전처리 버전, 평가 기준·결과, 기존 AI와의 호환 |
| DB migration | 이전 앱과의 호환, 배포 실패 시 복구 방법 |

계산 결과를 맞추려고 정답 파일만 수정하지 않습니다. 새 정답에는 입력·규칙·계산 근거·검토자를 남깁니다. 한 계산 안에서 서로 다른 모델 버전을 섞지 않습니다. 이미 반영한 migration은 덮어쓰지 않고 후속 파일로 변경을 남깁니다.

공식 산출물의 **Test Case 5~8개 권고는 보고서 작성 기준**입니다. 코드의 단위 테스트 개수를 8개 이하로 제한하는 뜻은 아닙니다. Must 요구사항은 모두 테스트에 연결합니다.

## 초기 설정과 리뷰 담당

첫 공통 커밋과 `main`·`dev`는 팀 개발을 시작하기 전에 준비합니다. 이후 보호 규칙을 적용하고, 각자 `feature`에서 작업합니다.

1. 이 문서와 `.github/` 템플릿을 기본 브랜치에 포함합니다.
2. `main`·`dev`의 PR 필수·직접 push 금지를 설정합니다. 승인 인원은 작성자를 제외하고 `main` 4명 이상, `dev` 1명 이상으로 정하며, `main`의 리뷰 대화 해결도 필수로 설정합니다.
3. **`main` 대상 PR이 같은 저장소의 `dev`에서 왔는지 확인하는 Jenkins 검사를 연결합니다.** 일반 PR 보호 설정만으로 출발 브랜치까지 제한되지는 않습니다.
4. 구현·테스트를 마치고 실제 등록된 검사만 GitHub 필수 상태 검사로 지정합니다. 출발 브랜치 검사는 PR 작성자가 바꿀 수 없는 신뢰한 설정에서 관리하고, PR 검사에는 운영 배포 자격증명을 제공하지 않습니다.
5. `feature → dev` PR 검사, `dev` 병합 후 통합 검증, `dev → main` PR의 배포 전 검증을 연결합니다. 기술 스택이 정해지면 포맷터·린터도 설정합니다.

`main` 병합 후 자동 배포 여부와 별도 승인 정책, `dev` 전용 서버는 아직 정하지 않았습니다. `main`에 병합됐다는 것과 배포에 성공했다는 것은 구분하며, 실제 배포 버전은 Jenkins 결과로 확인합니다. 설정 방법은 [브랜치 보호 안내](docs/infra/github-rules.md)를 따릅니다.

리뷰는 변경한 영역의 담당자에게 요청합니다. Front는 `front/`, Back은 `back/`, AI는 `ai-data/ai-service/`, ML은 `ai-data/ml-service/`·`ai-data/training/`이 기본 담당 범위입니다. 인프라는 루트 Compose·`Jenkinsfile`·`infra/`·`docs/infra/`를 맡고, `contracts/`와 통합 테스트는 연결되는 파트가 함께 확인합니다.
