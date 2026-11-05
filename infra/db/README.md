# PostgreSQL 개발 설정

DB는 **PostgreSQL 17.11-bookworm** 공식 이미지를 사용한다. 이미지 태그와 digest는 `compose.yaml`에서 고정하며 별도 Dockerfile은 없다. 호스트 포트는 열지 않고 Back이 내부 주소 `db:5432`로 접속한다.

## 계정과 최초 초기화

- `postgres`: 초기화·관리용 계정. 비밀번호는 `POSTGRES_PASSWORD`로 전달한다.
- 기본 `port8282_app`: Back이 사용하는 일반 로그인 계정. `DB_APP_USER`·`DB_APP_PASSWORD`로 지정한다.
- `init/10-app-user.sh`: 빈 DB 볼륨을 처음 초기화할 때 앱 계정을 만들고, 지정 DB 접속과 public 스키마의 사용·생성 권한을 부여한다.

앱 계정은 superuser가 아니다. 이 초기화 스크립트는 업무 테이블을 만들지 않으며, 업무 schema·migration은 Back 담당 영역이다. DB healthcheck는 앱 계정으로 TCP 인증 후 `SELECT 1`을 실행한다. Back의 `compose` 프로필도 실제 JDBC 연결을 확인한다.

`.env.example`의 비밀번호는 공개된 로컬 예시다. 운영·공유 서버에는 별도의 비밀값·권한·백업 정책이 필요하다.

## 데이터 유지

`postgres_data` 명명 볼륨을 `/var/lib/postgresql/data`에 연결한다. 기본 Compose 프로젝트의 볼륨 이름은 `port8282_postgres_data`다. 일반 종료는 저장소 루트에서 다음을 사용한다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml down
```

이 명령은 DB 볼륨을 지우지 않는다. 데이터 볼륨이 남으면 컨테이너를 다시 만들어도 기존 DB를 사용한다. 볼륨 보관은 백업이 아니며 별도 저장소로 백업하고 복원하는 절차는 이후 구성한다.

## 설정을 바꿀 때

DB 초기화 환경변수와 init 스크립트는 **빈 데이터 디렉토리를 만드는 첫 실행에만 적용**된다. 기존 DB가 있는 상태에서 `.env`의 비밀번호·DB명·계정명을 바꿔도 DB 내부 계정이 자동으로 바뀌지 않는다.

기존 데이터를 유지하려면 DB에서 계정·비밀번호 변경을 먼저 계획하고 Back의 접속 설정을 함께 맞춘다. 단순 접속 오류를 해결하려고 기존 볼륨을 삭제하지 않는다. 새 패치 이미지로 갱신할 때에도 데이터 백업·호환·복원 절차를 확인한다.

관리 명령은 `docker compose ... exec db psql` 방식으로 컨테이너 안에서 실행할 수 있다. 실제 비밀번호는 명령 기록·로그·문서에 출력하지 않는다.

[Compose 안내](../../docs/infra/compose.md) · [실행 명세](../../docs/infra/specification.md) · [PostgreSQL 공식 이미지](https://hub.docker.com/_/postgres)
