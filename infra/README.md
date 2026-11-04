# Infra · 공통 실행과 배포

인프라 담당자가 전체 연결·배포 규칙을 관리하고, 각 서비스 담당자와 실행 명령·포트·환경변수·준비 상태를 합의한다.

- `proxy/`: 화면/API 라우팅, TLS, 실시간 연결 설정.
- `jenkins/`: Controller·Agent 환경, 권한, 모델 출시와 코드 배포 작업 구성.
- `scripts/`: 배포·상태 확인·이전 앱 버전 복구·DB 백업/복원.

Compose 파일과 Jenkinsfile은 레포 루트에 둔다. Compose는 `compose.yaml` 공통, `compose.dev.yaml` 로컬 개발, `compose.prod.yaml` 서버 배포로 분리한다. 이 디렉토리에 별도의 앱 소스를 복제하지 않는다.

운영 서버는 Registry의 검증된 고정 이미지를 실행한다. 앱 서버에서 임의의 최신 코드를 pull하여 다시 빌드하는 방식과 혼용하지 않는다.

실제 DB 데이터, Jenkins 상태, 백업 파일은 Git 밖에 보관한다. 볼륨 경로와 백업 위치·복원 절차는 3단계에서 확정한다.
