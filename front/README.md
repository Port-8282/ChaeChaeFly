# Front · 대시보드

선박·부두·기상 상태, 계산 진행 상태, 접안 후보와 예상 비용을 보여준다. 담당자는 후보를 선택하고 사유를 입력한다.

- 브라우저는 프록시의 API 경로를 통해 Back과 통신한다. AI·ML·DB에 직접 연결하지 않는다.
- 상태 변화와 계산 결과를 자동 갱신한다. SSE·WebSocket 등 구체적인 전달 방식은 Back과 합의한다.
- 계산 중/실패/이전 결과 상태를 구분한다. 이전 결과를 최신 계산 결과처럼 표시하지 않는다.
- 선택 요청에는 계산 ID, 후보 ID, 담당자의 사유가 필요하다.

## Compose 개발 — 팀 공통 방식

Docker를 실행하고 저장소 루트에서 `.env.example`을 `.env`로 준비한 뒤 실행한다. 호스트에 Node.js·npm을 설치하지 않아도 된다. 전체 준비와 Windows 복사 명령은 [Compose 안내](../docs/infra/compose.md)를 따른다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

`http://127.0.0.1:8282`에 접속한다. Dockerfile의 `development` target에서 Vite를 내부 8080으로 실행하고 Proxy가 화면 요청을 전달한다. 소스 변경은 Watch가 동기화하고 Vite가 반영한다. API 요청은 Proxy가 Back으로 전달한다. `/api/health`는 Back·DB 상태 확인이며 `/health`는 Proxy 상태다.

다른 터미널에서 빌드를 확인할 수 있다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec front npm run build
```

현재 Front 기능 테스트는 아직 없다. 컨테이너 내부에서만 수정한 파일은 호스트 Git에 자동으로 돌아오지 않으므로 소스는 저장소에서 수정한다. 의존성 변경 시 package.json과 생성된 package-lock.json을 함께 갱신한다. IDE 디버거 연결은 별도 설정 대상이다.

## 호스트 설치·실행 — 선택 사항

Node.js 24.18.0과 npm 11.16.0을 사용한다. Vue 3.5.44, Vite 8.3.5의 최소 JavaScript 프로젝트다. Python용 `.venv`는 만들지 않는다. 현재 화면은 환경 확인용이며 대시보드 업무 기능은 구현 전이다.

최신 코드를 받은 뒤 이 `front/` 폴더에서 실행한다.

```bash
node --version
npm --version
npm ci
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`을 연다. 종료는 Ctrl+C다. 5173이 사용 중이면 오류로 종료하므로 먼저 다른 프로세스의 사용 여부를 확인한다.

`.nvmrc`·`.node-version`은 버전 정보이며 파일을 받는 것만으로 Node가 설치되지는 않는다. nvm을 사용하는 macOS·Linux 팀원은 이 폴더에서 `nvm install`과 `nvm use`로 지정 버전을 선택한다. 다른 환경은 [Node.js 설치 안내](https://nodejs.org/en/download)를 따른다. npm 버전이 다르면 선택한 Node 환경에서 `npm install --global npm@11.16.0`으로 맞춘다. 정확한 버전이 아니면 설치·실행이 중단되도록 설정했다.

## 빌드·Back 연결 확인

```bash
npm run build
npm run preview
```

빌드 결과는 `dist/`에 생성된다. preview는 `http://127.0.0.1:4173`에서 정적 화면을 확인하는 용도이며 개발용 API 프록시·운영 배포를 대신하지 않는다.

`npm run dev`로 실행한 서버는 `/api`와 `/actuator` 요청을 `http://127.0.0.1:8080`의 Back으로 전달한다. 경로는 그대로 유지하며 `/api` 업무 기능은 아직 구현 전이다. Back과 Front를 실행한 상태에서 다음으로 연결을 확인한다.

```bash
curl http://127.0.0.1:5173/actuator/health
```

응답의 `status` 값이 `UP`인지 확인한다. 이는 Back 프로세스의 상태 확인이며 DB·AI·ML 연결 성공을 의미하지 않는다. Back 주소를 바꾸려면 `.env.example`을 `.env.local`로 복사하고 `BACKEND_URL`을 수정한 뒤 개발 서버를 다시 시작한다. 기본 주소라면 파일을 복사하지 않아도 된다. `VITE_` 변수는 브라우저에 공개되므로 비밀값을 넣지 않는다.

## Git 공유 기준

- 버전 파일, `package.json`, 실제 생성한 `package-lock.json`, Vite 설정, 소스 코드는 함께 공유한다.
- `node_modules/`, `dist/`, `.env.local`은 Git에 올리지 않는다.
- 의존성을 변경할 때는 `npm install 패키지명`을 사용하고 `package.json`·`package-lock.json`을 같은 PR에 포함한다. 팀원과 CI의 재설치는 `npm ci`를 사용한다.
- 현재 기능 테스트는 없다. 이번 검증 범위는 설치·빌드·개발 서버와 Back 상태 확인 요청이다.

[전체 개발 환경 안내](../docs/infra/local-setup.md)

## Docker 실행

저장소 루트에서 실행한다. Docker Desktop(또는 Docker Engine + BuildKit)이 실행 중이면 호스트에 Node.js·npm을 따로 설치하지 않아도 된다.

```bash
docker build -t port8282-front:local ./front
docker run --rm --name port8282-front-local -p 127.0.0.1:3000:8080 port8282-front:local
```

브라우저에서 `http://127.0.0.1:3000`을 연다. 다른 터미널에서 `docker stop port8282-front-local`로 종료한다. `--rm`으로 실행했으므로 종료한 컨테이너는 지워지고 이미지는 남는다.

Dockerfile의 첫 단계는 Node.js 24.18.0·npm 11.16.0으로 `npm ci`와 `npm run build`를 실행한다. 마지막 단계는 Nginx에서 빌드된 화면만 제공한다. Node.js·node_modules는 실행 이미지에 복사하지 않는다. 기본 이미지의 태그와 digest를 함께 고정했으므로 버전 갱신 시 둘을 함께 수정한다.

- 내부 포트: 8080. 로컬 확인용 호스트 포트: 3000.
- `/health`: 정적 서버의 상태 확인. DB·Back·AI 연결 확인은 아니다.
- `nginx.conf`: 정적 파일·SPA 경로 처리, 비관리자 사용자 실행을 위한 임시 경로 설정.
- 이 기본 runtime 이미지는 빌드 시점의 화면을 제공하므로 소스 수정 후 다시 빌드한다. 개발용 자동 반영은 위 Compose 방식의 development target을 사용한다.
- Vite 개발 프록시는 이 runtime 이미지에서 실행하지 않는다. 단독 실행의 `/api`, `/actuator`는 404다. Compose에서는 별도의 `proxy` 서비스가 API를 Back으로 전달한다.

[전체 Docker 빌드·실행 안내](../docs/infra/docker.md)
