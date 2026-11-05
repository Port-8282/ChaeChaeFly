# 프록시 설정

`compose.yaml`이 공식 Nginx 이미지를 실행하고 이 폴더의 `nginx.conf`를 읽기 전용으로 연결한다. 별도 Dockerfile은 없다. 기본 진입점은 **http://127.0.0.1:8282**이며 호스트에 공개하는 앱 포트는 이 하나다.

| 요청 | 전달 위치 |
| --- | --- |
| `/` 및 화면 경로 | `front:8080` |
| `/health` | Proxy 자체 상태 응답 |
| `/api/health` | `back:8080/actuator/health` |
| 그 밖의 `/api`·`/api/...` | 경로를 유지하여 `back:8080`으로 전달 |
| `/actuator`·`/actuator/...` | 404, 외부 접근 차단 |

개발 환경의 Front는 Vite, 실행 이미지의 Front는 정적 Nginx 서버다. 프록시는 둘 다 같은 내부 8080으로 연결한다. Docker DNS를 주기적으로 다시 조회해 컨테이너 재생성으로 바뀐 IP를 따라간다. WebSocket Upgrade와 버퍼링 해제 설정을 포함하며 실제 업무 SSE·WebSocket 규격은 담당자와 합의한다.

Proxy `/health`가 정상이어도 다른 서비스의 업무 기능이 정상이라는 뜻은 아니다. `/api/health`는 Back의 `compose` 프로필에서 DB 연결 상태까지 포함한다. AI·ML의 업무 준비 상태는 별도 구현 대상이다.

설정 변경 후에는 저장소 루트에서 Proxy를 재생성한다. 애플리케이션 소스용 Compose Watch가 이 파일을 자동 반영하지는 않는다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --no-deps --force-recreate proxy
```

TLS·도메인·외부 접근 정책은 운영 서버를 정한 뒤 구성한다. 현재 설정을 공개 운영 서버용 보안·인증 구성으로 취급하지 않는다. 인증서 비밀키는 Git에 넣지 않는다. Jenkins 관리 화면은 앱 프록시와 별도 접근 정책을 사용한다.

[전체 Compose 안내](../../docs/infra/compose.md)
