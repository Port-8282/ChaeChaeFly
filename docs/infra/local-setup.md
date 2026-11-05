# 로컬 개발 환경

Vue 기본 화면과 Spring Boot 상태 확인 서버, AI·ML의 독립 uv 개발 환경 및 FastAPI 상태 확인 API를 구성했다. 네 서비스는 로컬 또는 Docker로 각각 실행할 수 있다. Docker만 사용하는 경우는 [Docker 사용 안내](docker.md)를 따른다. 개발용 Compose와 Back의 PostgreSQL 연결을 구성했다. 업무 API·AI→ML 업무 호출은 구현 전이고 모델 학습 환경은 보류한다. Jenkins CI는 [별도 안내](ci.md)에 따라 구성한다. 아래 명령은 최신 설정을 작업 브랜치에 반영한 뒤 실행한다.

## Docker로 팀 개발 환경을 구성할 때

팀 공통 시작 방법은 [Compose 개발 안내](compose.md)를 따른다. Git·Docker와 편집기가 있으면 호스트에 Node·JDK·uv를 설치하지 않고 컨테이너 안에서 실행·빌드·검사할 수 있다. 코드 자동 반영은 `up --build --watch`로 실행할 때 동작한다. IDE 자동완성·중단점 디버깅 연결은 편집기별 추가 설정이 필요하다.

아래 내용은 컨테이너 밖에서 직접 개발하려는 팀원을 위한 선택 사항이다. 공유한 버전·lock 파일은 Docker에서도 동일하게 사용한다.

## 환경 기준

| 영역 | 기준 | 현재 상태 |
| --- | --- | --- |
| Front | Vue 3.5.44·Vite 8.3.5 / Node.js 24.18.0·npm 11.16.0 | 설치·빌드·기본 화면 |
| Back | Spring Boot 4.1.2 / JDK 21·Gradle Wrapper 9.8.2 | 빌드·상태 확인 서버 |
| AI | Python 3.12.13·독립 uv 프로젝트 | 패키지 설정·lock 파일·상태 확인 API |
| ML 추론 | Python 3.12.13·독립 uv 프로젝트 | 패키지 설정·lock 파일·상태 확인 API |
| 모델 학습 | 필요할 때 별도 환경 | 현재 보류 |

uv는 0.12.14 이상을 사용하며 초기 검증 기준은 0.12.14다. 설치되어 있지 않으면 [공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)를 따른다. Python 패치 버전은 두 `.python-version`에 `3.12.13`으로 지정했고, 패키지의 지원 범위는 `>=3.12,<3.13`이다.

## Front: Vue·npm

Node.js와 npm은 먼저 설치해야 한다. `.nvmrc`·`.node-version`·`packageManager`를 Git으로 받아도 도구가 자동 설치·전환되지는 않는다. 설치 방법은 [Node.js 공식 안내](https://nodejs.org/en/download)를 따른다.

macOS·Linux에서 nvm을 이미 사용한다면 `front/`에서 다음으로 버전을 선택한다.

```bash
nvm install
nvm use
node --version
npm --version
```

예상 값은 Node `v24.18.0`, npm `11.16.0`이다. npm이 다르면 선택한 Node 환경에서 `npm install --global npm@11.16.0`을 실행한다. Windows 등 다른 환경은 사용하는 설치 도구로 같은 버전을 준비한다. 버전 불일치는 설치·실행 오류로 알려주며, 강제로 무시하기보다 지정 버전에 맞춘다.

아래는 **저장소 루트**에서 실행한다.

```bash
npm --prefix front ci
npm --prefix front run build
npm --prefix front run dev
```

`http://127.0.0.1:5173`에 기본 화면이 열린다. `npm ci`는 기존 `node_modules`를 정리하고 lock 파일대로 다시 설치하며 lock 파일을 변경하지 않는다. `npm run build` 결과는 `front/dist/`에 생성된다. 개발 서버 종료는 Ctrl+C다.

Vite 개발 서버의 `/api`, `/actuator` 요청은 Back의 `http://127.0.0.1:8080`으로 전달한다. `/api` 업무 기능은 아직 구현 전이다. 주소 변경이 필요하면 `front/.env.example`을 `front/.env.local`로 복사해 `BACKEND_URL`을 바꾸고 서버를 다시 시작한다. 기본값 사용 시 복사가 필요 없다. `VITE_` 변수는 브라우저에 공개되므로 비밀값을 넣지 않는다. 이 프록시는 로컬 개발용이며 운영 프록시 설정은 이후 별도로 구성한다.

## Back: Spring Boot·Gradle

JDK 21을 먼저 준비한다. 예를 들어 [Eclipse Temurin JDK 21](https://adoptium.net/temurin/releases/?version=21)처럼 운영체제·CPU에 맞는 JDK를 설치한다. `java -version`, `javac -version`이 21인지 확인하고 터미널의 `JAVA_HOME`과 IDE의 Gradle JVM도 JDK 21로 맞춘다. `.java-version`은 버전 안내이며 JDK를 자동으로 설치하지 않는다.

Gradle을 따로 설치할 필요는 없다. Git에 포함된 Wrapper가 Gradle 9.8.2를 내려받으며 다운로드 checksum을 확인한다. 첫 실행에는 Gradle과 Java 의존성을 받을 인터넷 연결이 필요하다. JDK 자동 다운로드 설정은 포함하지 않았다.

**저장소 루트**에서 실행한다.

```bash
java -version
javac -version
./back/gradlew -p back build
./back/gradlew -p back bootRun
```

Windows PowerShell에서는 다음을 사용한다.

```powershell
.\back\gradlew.bat -p back build
.\back\gradlew.bat -p back bootRun
```

`http://127.0.0.1:8080/actuator/health` 응답의 `status` 값이 `UP`인지 확인한다. 단독 실행의 기본 `local` 프로필은 DB 없이 동작한다. Compose에서는 `compose` 프로필을 사용하고 JDBC DB 상태를 함께 확인한다. 테스트는 임의의 사용 가능한 포트에서 실제 health HTTP 응답을 확인한다. 개발 서버 종료는 Ctrl+C다.

`SERVER_PORT` 환경변수로 Back 포트를 바꿀 수 있다. 이때 Front의 `BACKEND_URL`도 맞춘다. Spring은 루트 `.env`를 자동으로 읽지 않으므로 환경변수는 터미널·IDE에서 전달한다. 포트가 이미 사용 중이라면 다른 프로세스를 임의로 종료하지 말고 사용자와 확인하거나 포트를 변경한다.

## Front → Back 연결 확인

Back과 Front를 서로 다른 터미널에서 실행한 뒤 다음을 확인한다.

```bash
curl http://127.0.0.1:8080/actuator/health
curl http://127.0.0.1:5173/actuator/health
```

두 응답 모두 `status`가 `UP`이어야 한다. `groups` 같은 추가 필드가 포함될 수 있다. Front 경유 요청만 실패하면 Vite가 실행 중인지, `BACKEND_URL`과 Back 포트가 일치하는지 확인한다. 현재 기본 화면에는 상태 확인 API 호출 기능을 넣지 않았다.

## AI·ML: 처음 설치하거나 최신 설정을 받은 뒤

저장소를 clone하고 [협업 규칙](../../CONTRIBUTING.md)을 읽는다. 최신 설정이 작업 브랜치에 반영된 상태에서 아래 명령을 **저장소 루트**에서 실행한다. `git pull` 자체는 가상환경을 만들지 않는다. 첫 설치에는 Python·패키지를 내려받을 네트워크 접근이 필요할 수 있다.

```bash
uv --version
uv sync --locked --project ai-data/ai-service
uv sync --locked --project ai-data/ml-service
```

AI만 담당하면 AI 명령만, ML만 담당하면 ML 명령만 실행해도 된다. uv는 없는 `.venv`를 생성하고, 기존 환경이면 lock 파일에 맞춰 설치 상태를 갱신한다. 필요한 Python이 없으면 uv의 기본 자동 다운로드 설정에 따라 준비한다.

```text
ai-data/ai-service/.venv/  → AI 코드 개발 환경
ai-data/ml-service/.venv/  → ML 추론 코드 개발 환경
```

`.venv`는 로컬 파일이므로 Git에 올리지 않는다. 공유 대상은 각 서비스의 `.python-version`, `pyproject.toml`, `uv.lock`이다. `requirements.txt`는 별도로 관리하지 않는다. `uv.lock`을 직접 수정하지 않는다.

## AI·ML 설치 확인

저장소 루트에서 실행한다. 두 명령의 Python 버전은 3.12.13이고, `sys.prefix`는 서로 다른 서비스의 `.venv`를 가리켜야 한다.

```bash
uv run --locked --project ai-data/ai-service python -c "import sys, port8282_ai; print(sys.version); print(sys.prefix); print(port8282_ai.__file__)"
uv run --locked --project ai-data/ml-service python -c "import sys, port8282_ml; print(sys.version); print(sys.prefix); print(port8282_ml.__file__)"
```

`uv run`을 사용하면 가상환경을 수동으로 활성화하지 않아도 된다. VS Code에서 AI를 작업할 때는 AI `.venv`의 Python을, ML을 작업할 때는 ML `.venv`의 Python을 선택한다. macOS·Linux는 `.venv/bin/python`, Windows는 `.venv/Scripts/python.exe`다. 서비스 폴더를 각각 별도 창으로 열면 선택하기 쉽다.

## 의존성 변경과 Git 공유

- Front: `front/`에서 `npm install 패키지명` 실행 후 `package.json`과 `package-lock.json`을 함께 공유한다. 팀원·CI 재설치는 `npm ci`다.
- Back: `build.gradle`을 수정하고 `back/`에서 `./gradlew dependencies --write-locks`로 잠금 정보를 갱신하고 `./gradlew build`로 검증한다. `build.gradle`과 `gradle.lockfile`을 함께 공유한다. 일반 팀원은 `--write-locks` 없이 `./gradlew build`를 실행한다.
- Gradle Wrapper의 스크립트·JAR·properties는 Git에 포함한다. Wrapper JAR는 모델 파일이나 빌드 결과와 달리 실행에 필요한 파일이다.
- Node/npm 버전 파일과 Python `.python-version`도 Git으로 공유한다. 설치 결과인 `node_modules`, `.venv`, `.gradle`, `build`, `dist`는 공유하지 않는다.
- 현재 Back은 JDK 21 계열을 요구한다. Python·Node와 달리 JDK의 패치 버전·배포판까지 고정한 구성은 아니다.

### AI·ML 의존성 추가

해당 **서비스 폴더**에서 `uv add <패키지명>`으로 실행용 의존성을 추가한다. 검사 도구는 `uv add --dev <패키지명>`으로 추가한다. uv가 변경한 `pyproject.toml`과 `uv.lock`을 같은 PR에 포함한다. 다른 팀원은 최신 설정을 받은 뒤 `uv sync --locked`를 실행한다.

실행용 의존성으로 FastAPI·Uvicorn을 추가했고 `pytest`·`ruff`는 개발 도구로 유지한다. Agent·최적화·모델 라이브러리는 담당 구현에 맞춰 추가한다. AI·ML API의 로컬 실행 명령은 각 서비스 README를 따른다. setuptools는 빌드 도구로 별도 고정하며 `uv.lock`은 프로젝트·개발 의존성의 확정 버전을 관리한다.

`--locked`는 lock 파일을 임의로 갱신하지 않는다. 설정과 lock 파일이 맞지 않으면 오류가 발생하므로, 변경 작성자가 의존성을 정리하고 lock 파일을 함께 갱신해야 한다.

## AI·ML 코드 검사와 테스트

아래 명령은 **각 서비스 폴더**에서 실행한다.

```bash
uv lock --check
uv run --locked ruff check src
uv run --locked ruff format --check src
```

테스트 작성 후에는 `uv run --locked pytest`를 사용한다. 현재 테스트 폴더는 비어 있으며 테스트 없음(exit 5)을 성공으로 처리하지 않는다. 패키지 import·환경 설치 확인은 서비스 기능 테스트와 다르다. Python 하위 패키지에는 `__init__.py`를 추가한다.

## Front·Back 검증 기록

2026-11-04, macOS arm64에서 지정 Node·npm과 JDK 21.0.12.1로 확인했다.

- 저장소 루트의 `npm --prefix front ci`와 `npm --prefix front run build` 성공. package-lock.json 변경 없음.
- `./back/gradlew -p back build --no-daemon` 성공. health HTTP 테스트 1개 통과(실패·스킵 0), gradle.lockfile 변경 없음.
- Front 5173의 HTML·Vue 모듈 응답 HTTP 200 확인.
- Back 8080의 health 응답과 Front 5173을 거친 프록시 응답 모두 HTTP 200, `status: UP` 확인.
- 검증용 서버는 종료했다. 업무 기능·DB·AI·ML 연동이나 Windows·Linux 실행 검증은 아직 하지 않았다.
- macOS 설치 중 선택 의존성 fsevents의 스크립트 승인 안내가 출력되었으나, 별도 승인 없이 위 설치·빌드·개발 서버 검증이 통과했다.

## AI·ML 초기 검증 기록

2026-11-04, macOS arm64에서 Python 3.12.13·uv 0.12.14로 두 환경을 확인했다. 설치된 개발 도구는 pytest 9.2.0, Ruff 0.17.3이다.

- lock 검사와 잠금 상태 재동기화 성공. 재동기화 전후 lock 파일 해시가 같았다.
- 소스 폴더 밖에서도 각 패키지를 import했으며, 서로 다른 .venv와 상대 서비스 패키지 미설치를 확인했다.
- 두 서비스의 Ruff 검사·포맷 확인을 통과했다.
- .venv의 Git 제외와 학습 환경 미생성을 확인했다.
- 당시 기능 테스트는 없으며 pytest 수집 결과는 0개(exit 5)였다. 당시에는 API·모델·Docker·다른 운영체제 검증을 하지 않았다. 이후 11월 5일 추가한 상태 확인 API·Docker 검증은 아래 기록을 따른다.

## Docker 추가 검증 기록

2026-11-05에 서비스별 Dockerfile 4개와 AI·ML의 FastAPI 상태 확인 API를 추가했다. Linux arm64 이미지 빌드, 네 서비스의 상태 응답·Docker health, 임시 네트워크의 DNS·HTTP 접근을 확인했다. 업무 최적화·모델 추론 성공을 뜻하지 않는다. 세부 결과와 Docker만 사용하는 방법은 [Docker 사용 안내](docker.md)를 따른다.

## 다음 단계

서비스별 Dockerfile과 `compose.yaml` + `compose.dev.yaml`, 프록시·PostgreSQL 연결을 구성했다. 다음은 업무 API 합의·구현과 Jenkins·서버 배포 설정이다. 컨테이너에서도 공유된 설정으로 환경을 구성하며 로컬 `.venv`를 이미지에 복사하지 않는다.

루트 `.env.example`은 Compose 로컬 개발용 양식이다. `.env`로 복사하며 실제 비밀값은 커밋하지 않는다. Compose가 필요한 변수만 서비스에 전달한다. 로컬에서 직접 실행하는 Spring·Python이 이 파일을 자동으로 읽지는 않는다. 모델 학습은 별도 환경이 필요해질 때 구성하며, 모델·전처리·추론 의존성의 호환성을 ML 담당자와 확인한다.

[uv 프로젝트 안내](https://docs.astral.sh/uv/guides/projects/) · [lock·동기화](https://docs.astral.sh/uv/concepts/projects/sync/) · [인프라 명세](specification.md) · [통합 검증](../../tests/integration/README.md)
