# 인프라 실행 명세 초안

> 미정 항목을 구현 전 합의하기 위한 문서다. 실제 서버나 포트가 구성되었다는 의미가 아니다.

## 정한 구조

- 레포: ChaeChaeFly. 팀·서비스 식별 이름: PORT 8282.
- Compose 프로젝트 이름 예시: port8282.
- 앱 서비스 이름: proxy, front, back, ai, ml, db.
- 배포 도구: Docker Compose. CI/CD: Jenkins.
- AI·ML·학습: 각각 독립 uv 프로젝트.
- AI → ML: 내부 HTTP + JSON. 서비스 이름으로 접근.
- DB 저장: 영속 볼륨. 백업은 별도 저장소·복원 절차.

## 확정할 실행 항목

각 서비스의 프레임워크·런타임 버전, 시작/테스트 명령, 내부 포트, 환경변수, 준비 상태 확인 방법, CPU·메모리 요구량을 담당자와 정한다. 모델 로드가 끝났는지 확인하는 ML 준비 상태와 Back의 기존 결과 조회 가능 상태를 분리한다.

서버 제공처·CPU 아키텍처·사양, DB 제품, Registry·모델 artifact 저장소, TLS·도메인, 실시간 전달 방식, Jenkins Controller/Agent 배치는 미정이다.

## 환경변수 초안

- COMPOSE_PROJECT_NAME: Compose 리소스 식별자.
- APP_ENV, TZ: 실행 환경·시간대.
- AI_BASE_URL: Back이 접근하는 AI 주소.
- ML_BASE_URL: AI가 접근하는 ML 주소.
- DATABASE_URL: Back·migration 작업에서 사용하는 DB 연결.
- LLM_API_BASE_URL, LLM_MODEL, LLM_API_KEY: AI의 LLM 연결 설정.

변수 이름과 용도는 구현 시 확정하고 .env.example과 함께 갱신한다. 실제 비밀번호·키를 이 문서에 적지 않는다. 외부 공개 앱 진입점은 프록시로 통합하고 AI·ML·DB는 내부 접근을 기본으로 한다.

[서비스 구성도](architecture.md) · [API 규격 기준](../../contracts/README.md)
