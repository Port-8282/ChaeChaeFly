# Infra · 공통 실행과 배포

인프라 담당자가 전체 연결·배포 규칙을 관리하고, 각 서비스 담당자와 실행 명령·포트·환경변수·준비 상태를 합의한다.

- `proxy/`: 화면/API 라우팅과 개발 HMR 연결. 운영 TLS는 미정.
- `db/init/`: PostgreSQL 17.11 최초 초기화 시 앱 전용 계정·권한 구성. 업무 테이블 migration과 구분.
- `jenkins/`: CI용 Controller·Agent·전용 Docker 환경. [설치 안내](../docs/infra/ci.md).
- `scripts/ci.py`: 현재 CI 실행·검사 결과·전용 자원 정리. 배포·복구·DB 백업 스크립트는 추후 작성.

Compose 파일과 Jenkinsfile은 레포 루트에 둔다. Compose는 `compose.yaml` 공통, `compose.dev.yaml` 로컬 개발, `compose.prod.yaml` 서버 배포로 분리한다. 이 디렉토리에 별도의 앱 소스를 복제하지 않는다.

운영 서버는 Registry의 검증된 고정 이미지를 실행한다. 앱 서버에서 임의의 최신 코드를 pull하여 다시 빌드하는 방식과 혼용하지 않는다.

실제 DB 데이터, Jenkins 상태, 백업 파일은 Git 밖에 보관한다. DB는 Compose의 postgres_data 볼륨을 /var/lib/postgresql/data에 연결했다. 별도 백업 위치·복원 절차는 이후 구성한다.
