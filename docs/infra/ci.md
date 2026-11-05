# Jenkins CI 구성

팀원마다 Jenkins를 설치하지 않습니다. 인프라 담당자가 공통 Jenkins 한 곳을 관리하고, 팀원은 코드를 올려 검사 결과를 확인합니다. **현재 범위는 검사·테스트·이미지 빌드입니다. 운영 배포는 하지 않습니다.**

## 전체 흐름

```text
팀원: feature 브랜치에서 작업 → dev로 PR
                               ↓
Jenkins Controller: 변경 발견·작업 예약·결과 표시
                               ↓
Jenkins Agent: 저장소 받기 → Compose 설정 검사
                               ↓
Front 빌드 → Back 빌드·테스트 → AI·ML 코드 검사·테스트
                               ↓
4개 실행 이미지의 기본 응답·AI → ML 통신 확인
                               ↓
JUnit·로그 보관 → 이번 검사에 만든 컨테이너·이미지 정리
```

`dev`, `main` 변경도 같은 CI 검사를 실행하도록 연결합니다. main에 합쳐졌다는 이유만으로 배포하지 않습니다. 처음에는 모든 서비스를 순서대로 검사하며, 변경 경로에 따른 선택 실행은 이후 검사 시간이 길어질 때 도입합니다.

## 앱 실행 환경과 분리합니다

```text
앱 개발 Compose                         Jenkins 전용 Compose
127.0.0.1:8282                           127.0.0.1:8081
Proxy · Front · Back · AI · ML · DB       Controller (빌드 executor 0)
                                                 ↑ WebSocket
                                        Agent (executor 1, ci-docker)
                                                 ↓ TLS
                                        CI 전용 Docker daemon
                                                 ↓
                                        검사할 이미지·임시 컨테이너
```

- Controller에는 Docker socket과 앱 DB 볼륨을 연결하지 않습니다.
- Agent는 TLS로 CI 전용 Docker daemon에 연결합니다. 개발 앱의 Docker socket은 연결하지 않습니다.
- 빌드 컨텍스트를 Docker에 전송하고 결과 파일은 `docker cp`로 가져옵니다. Agent의 경로를 다른 daemon의 호스트 경로로 가정하지 않습니다.
- CI Docker 캐시는 별도 볼륨에 남고, 매 실행의 임시 자원은 고유 이름으로 정리합니다. 개발용 `port8282` 컨테이너·볼륨은 CI 정리 대상이 아닙니다.
- Docker-in-Docker는 `privileged` 권한을 사용합니다. 이것은 가상머신 수준의 격리가 아닙니다. 현재는 신뢰하는 팀 저장소의 코드만 실행하고 외부 fork PR 자동 실행은 사용하지 않습니다. 상시 운영 시 CI 전용 호스트를 사용하는 방향입니다.

## 무엇을 검사하나요?

| 대상 | 현재 검사 | 아직 확인하지 않는 것 |
| --- | --- | --- |
| Compose | 공통 설정과 공통+개발 설정 문법·변수 구성 | 운영 Compose, 서버 배포 |
| Front | lock 기반 설치·Vue/Vite 빌드·실행 이미지 응답 | 화면 기능 테스트: 현재 미작성 |
| Back | Gradle lock 기반 빌드·기존 HTTP 상태 테스트·실행 응답 | 실제 업무 API, 이번 CI에서의 DB 연동 |
| AI·ML | uv lock 기반 설치·Ruff·실행 응답 | 기능 테스트: 현재 미작성, 실제 최적화·모델 정확도 |
| 연결 | AI 컨테이너에서 ML 상태 API 호출 | 스케줄 입력부터 보고서까지 전체 업무 흐름 |

Front의 `test` 명령과 Python 테스트 파일이 추가되면 CI가 실행합니다. **테스트가 없는 것은 JUnit에 skipped로 기록하며 테스트 통과라고 쓰지 않습니다.** 테스트 파일이 있는데 수집되지 않거나 실패하면 CI도 실패합니다. Back smoke는 `local` 프로필로 실행하므로 DB 연결 성공을 뜻하지 않습니다. 개발 Compose의 Back·DB 검증과 구분합니다.

## 저장소 파일

- `Jenkinsfile`: 검사 순서·제한 시간·결과 보관.
- `infra/scripts/ci.py`: Docker 빌드·검사·기본 응답 확인·자원 정리.
- `infra/jenkins/`: Controller·Agent 이미지, 전용 Compose, 플러그인 버전.
- `ci-results/`: 실행 중 생성되는 로그·JUnit·상태. Git 제외.

서비스 담당자는 테스트와 의존성 lock 파일을 관리하고, 인프라 담당자는 Jenkins 실행 환경과 연결을 관리합니다. 기존 서비스 Dockerfile의 빌드·개발·실행 단계를 재사용합니다.

## 인프라 담당자: 최초 설정

아래 명령은 저장소 루트에서 실행합니다. 다른 팀원에게 매번 시키는 작업이 아닙니다. Docker Desktop이 실행 중이어야 합니다.

1. `infra/jenkins/.env.example`을 같은 폴더의 `.env`로 복사합니다. 기존 파일은 덮어쓰지 않습니다.

```bash
# macOS·Linux
cp infra/jenkins/.env.example infra/jenkins/.env
```

Windows PowerShell은 `Copy-Item infra/jenkins/.env.example infra/jenkins/.env`를 사용합니다. 이 파일은 앱용 루트 `.env`와 다르며 Git에서 제외됩니다.

2. Controller·빌드 환경 이미지를 준비하고 Controller와 CI Docker를 실행합니다.

```bash
docker compose -p port8282-ci --env-file infra/jenkins/.env -f infra/jenkins/compose.yaml --profile agent build
docker compose -p port8282-ci --env-file infra/jenkins/.env -f infra/jenkins/compose.yaml up -d jenkins docker
```

3. `http://127.0.0.1:8081`에서 초기 설정을 진행합니다. 최초 해제 비밀번호는 아래 명령으로 **본인 터미널에서만** 확인합니다. 채팅·PR에 붙여 넣지 않습니다.

```bash
docker compose -p port8282-ci --env-file infra/jenkins/.env -f infra/jenkins/compose.yaml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

프로젝트 이미지에 필요한 플러그인을 설치해 두었습니다. 추가 플러그인은 필요할 때 검토해 설치합니다. 관리자 계정을 만들고 Controller의 executor가 `0`인지 확인합니다.

4. Jenkins의 **Manage Jenkins → Nodes → New Node**에서 Agent를 등록합니다.

- 이름: `ci-docker`, 유형: Permanent Agent.
- Remote root directory: `/home/jenkins/agent`.
- Executors: `1`, Labels: `ci-docker`.
- Usage: 해당 label을 지정한 작업만 실행.
- Launch method: Controller에 연결하는 inbound Agent.

저장 후 노드 페이지의 접속 secret을 `infra/jenkins/.env`의 `JENKINS_AGENT_SECRET`에 넣습니다. Secret을 Jenkinsfile에 쓰지 않습니다. Agent는 WebSocket으로 Controller에 접속하므로 50000 포트를 공개하지 않습니다.

```bash
docker compose -p port8282-ci --env-file infra/jenkins/.env -f infra/jenkins/compose.yaml --profile agent up -d
```

Jenkins 노드 목록에서 `ci-docker`가 online인지 확인합니다. Controller가 요청을 예약하더라도 Agent가 offline이면 검사가 시작되지 않습니다.

## GitHub 연결: 파일을 올린 뒤 한 번 설정

**현재 로컬 파일을 추가한 것만으로 GitHub PR 검사가 켜지지는 않습니다.** 이 변경을 사용자가 검토해 원격 브랜치에 올린 뒤 연결합니다. 이 작업에서는 commit·push·원격 설정 변경을 하지 않습니다.

1. Jenkins에 GitHub 저장소 접근용 Credentials를 등록합니다. 조직 저장소에는 해당 저장소만 허용한 GitHub App 방식을 권장합니다. 최소 필요 권한은 공식 [GitHub App 연결 안내](https://github.com/jenkinsci/github-branch-source-plugin/blob/master/docs/github-app.adoc)를 확인합니다. 운영 SSH 키·Registry 쓰기 권한은 넣지 않습니다.
2. New Item → **Multibranch Pipeline**, 이름은 `port8282-ci`로 만듭니다.
3. Branch Sources → GitHub에서 `Port-8282/ChaeChaeFly`와 Credentials를 연결합니다.
4. Origin PR 발견은 **대상 브랜치와 병합한 버전 검사**를 선택합니다. Branch 발견을 켜고 이름 필터는 `main dev PR-*`로 제한합니다. 외부 fork PR 발견 기능은 추가하지 않습니다.
5. Build Configuration의 Script Path는 루트 `Jenkinsfile`입니다.
6. 로컬에서는 주기적 스캔(예: 5분)을 켭니다. `localhost`는 GitHub가 접근할 수 없으므로 webhook 주소로 등록하지 않습니다. 공용 Jenkins URL을 확보한 뒤 HTTPS webhook을 연결할 수 있습니다.
7. 수동 Scan으로 PR/브랜치를 발견하고 빌드합니다. 실제 Jenkins 결과와 GitHub 상태가 연결된 것을 확인한 뒤, 그 **실제 검사 이름**을 필수 상태 검사로 등록합니다.

Jenkinsfile은 PR 코드의 일부입니다. main에 같은 저장소의 dev만 병합하도록 강제하는 신뢰한 검사와 승인 규칙 설정은 [브랜치 보호 안내](github-rules.md)에 따라 별도 구현·설정합니다. 이 CI가 그 보호 규칙을 이미 강제한다고 보지 않습니다.

## 검사가 실패하면

Jenkins 단계 이름으로 실패 위치를 확인하고 Console Output과 `ci-results` 보관 파일을 봅니다. 실패를 숨기기 위해 테스트 명령에 `|| true`를 붙이지 않습니다. 수정 후 PR에 새 커밋을 올리면 다시 검사합니다.

- Front 의존성 변경: `package.json`과 `package-lock.json` 함께 반영.
- Python 의존성 변경: `pyproject.toml`과 실제 생성한 `uv.lock` 함께 반영.
- Back 의존성 변경: Gradle 설정과 재생성·검토한 `gradle.lockfile` 함께 반영.
- Agent offline: 노드 secret·컨테이너 로그·Controller URL 확인.
- Docker 연결 실패: CI Docker의 상태·TLS 인증서 연결 확인.

CI만 종료하려면 아래 명령을 사용합니다. 앱 개발 환경과 Jenkins 상태·캐시 볼륨은 유지됩니다.

```bash
docker compose -p port8282-ci --env-file infra/jenkins/.env -f infra/jenkins/compose.yaml --profile agent down
```

## 검증 기록 — 2026-11-05

macOS Docker Desktop의 Linux arm64 환경에서 확인했습니다.

- Controller·Agent 이미지 빌드, CI Docker TLS 연결 성공.
- Controller executor 0, `ci-docker` Agent executor 1·online 확인.
- 실제 Jenkins Pipeline 문법 검증 성공.
- 전용 Agent·Docker에서 Compose 검사, 4개 앱 이미지 빌드, Back 테스트, AI·ML Ruff, 실행 응답·AI → ML 통신, 자원 정리 성공.
- Jenkins 로컬 검증 작업 `port8282-local-ci-check`의 1번 빌드 결과: **SUCCESS**. JUnit 11개 항목 중 8개 통과·3개 skipped. 통과 항목에는 CI 단계 상태가 포함되며 업무 기능 테스트 8개를 뜻하지 않습니다.
- Front·AI·ML의 미작성 기능 테스트 3개는 skipped로 표시됨을 확인했습니다.
- 임시 복사본에 실패하는 Python 테스트를 넣었을 때 CI가 종료 코드 1로 실패하고 JUnit 실패 결과를 남기는 것까지 확인했습니다. 실제 소스에는 이 테스트를 추가하지 않았습니다.
- 기존 앱 6개 컨테이너와 DB 볼륨은 유지했습니다.

로컬 검증 작업은 GitHub checkout 대신 **당시 소스 복사본**을 넣어 실행했습니다. 이 작업은 기록 확인용으로 비활성화했습니다. 실제 `checkout scm`, GitHub PR 탐색·자동 실행·상태 보고·필수 검사 설정은 아직 검증하지 않았습니다. Windows 호스트·Linux amd64 실행도 별도 확인이 필요합니다.

**현재 이 PC에는 Controller·CI Docker·Agent가 실행 중이며 Agent 등록까지 완료했습니다.** 다른 PC의 최초 설치는 위 절차를 따릅니다. 이 PC에서는 Jenkins에 처음 접속해 초기 관리자 설정을 마친 뒤, 파일 검토·push 후 GitHub 연결 단계로 진행하면 됩니다. 접속은 [로컬 Jenkins](http://127.0.0.1:8081), 검증 결과는 [로컬 CI 1번 빌드](http://127.0.0.1:8081/job/port8282-local-ci-check/1/)에서 확인합니다.

강제 종료로 post 정리가 실행되지 않으면 CI Docker에 임시 자원이 남을 수 있습니다. 재시도 전에 실행별 `io.port8282.ci-run` 라벨과 해당 작업을 확인해 CI 자원만 정리합니다. 개발 Docker에서 전역 prune을 실행하지 않습니다. 캐시·Jenkins 상태 볼륨의 보관·백업 정책은 별도 관리합니다.

## 근거

- [Jenkins Controller 분리](https://www.jenkins.io/doc/book/security/controller-isolation/)
- [Jenkins Docker 설치](https://www.jenkins.io/doc/book/installing/docker/)
- [Multibranch Pipeline](https://www.jenkins.io/doc/book/pipeline/multibranch/)
- [GitHub Branch Source](https://plugins.jenkins.io/github-branch-source/)
