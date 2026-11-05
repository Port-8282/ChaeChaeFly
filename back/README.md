# Back · Spring 개발 환경

Spring Boot 초기 서버와 HTTP 상태 확인 테스트를 구성했다. Compose에서 PostgreSQL에 연결하는 JDBC 설정을 추가했다. 업무 API·테이블·AI 호출은 구현 전이다.

향후 이벤트를 받아 상태를 갱신하고 AI에 계산을 요청하며, DB 저장·조회와 대시보드 갱신을 담당한다.

- JSON 검증, 중복 이벤트 처리, 상태 버전 증가를 한 흐름으로 관리한다.
- 계산 요청을 DB에 기록하고 작업 ID를 반환한다. 요청 처리와 긴 AI 계산 실행을 분리한다.
- 초기에는 Back 내부의 제한된 작업 실행 코드와 DB 작업 기록을 사용한다. 별도 큐 컨테이너는 현재 설계에 넣지 않는다.
- 여러 실행자가 같은 작업을 처리하지 않도록 작업 점유와 만료·재시도 규칙을 구현한다.
- 오래된 계산은 이력으로 보관하고 최신 추천을 덮어쓰지 못하게 한다.
- 선택 당시 후보·비용·모델 버전·사유를 보존하여 보고서를 요청한다.
- ML이 갱신 중이어도 DB에 저장된 결과를 조회할 수 있도록 조회 상태와 계산 가능 상태를 구분한다.

DB migration 파일은 이 서비스가 소유한다. 배포 시 별도 일회성 작업으로 실행하며 앱 인스턴스마다 무조건 실행하지 않는다.

## 처음 설치하거나 pull한 뒤

JDK 21을 먼저 설치하고 `java -version`에서 21인지 확인한다. `.java-version`은 팀 기준을 기록한 파일이며 JDK를 자동 설치하지 않는다. IDE의 프로젝트 SDK와 Gradle JVM도 21로 맞춘다. Gradle은 따로 설치하지 않아도 된다.

저장소 루트에서 실행한다.

```bash
cd back
java -version
./gradlew build
./gradlew bootRun
```

Windows PowerShell에서는 `./gradlew.bat build`, `./gradlew.bat bootRun`을 사용한다. 첫 빌드는 Gradle·라이브러리를 내려받으므로 네트워크 연결이 필요하다.

기본 주소는 `http://localhost:8080`이다. 서버가 실행된 상태에서 `http://localhost:8080/actuator/health`를 열면 응답의 `status` 값이 `UP`인지 확인할 수 있다. 별도 프로필을 지정하지 않은 단독 실행은 `local` 프로필이며 DB 연결 없이 Spring 서버 상태를 확인한다. Compose의 `compose` 프로필은 PostgreSQL 연결도 확인한다. 어느 경우에도 AI·ML 업무 기능의 준비 완료를 의미하지 않는다. 포트가 사용 중이면 `SERVER_PORT` 환경변수로 다른 포트를 지정한다.

## 공유하는 기준

| 항목 | 버전·설정 |
| --- | --- |
| Java | JDK 21 (`.java-version`, Java toolchain) |
| Spring Boot | 4.1.2 |
| Gradle | Wrapper 9.8.2 |
| Spring 의존성 관리 플러그인 | 1.1.7 |
| 라이브러리 | `build.gradle` + 실제 생성한 `gradle.lockfile` |
| 실행 확인 | `GET /actuator/health` |

Wrapper는 [공식 Spring Initializr](https://start.spring.io/)에서 생성했고 Gradle 공식 체크섬과 대조했다. `gradle-wrapper.properties`의 배포 파일 SHA256으로 다운로드를 검증한다. Wrapper 파일 전체와 `gradle.lockfile`을 Git에 함께 올린다. `.gradle/`, `build/`, 설치한 JDK는 Git에 올리지 않는다. JDK는 21 계열을 기준으로 하며 패치·배포판까지 동일하게 고정한 것은 아니다.

`./gradlew build`는 컴파일·테스트·JAR 생성을 수행한다. 테스트는 임의의 빈 포트에서 서버를 띄워 실제 HTTP 상태 응답을 확인하므로 8080을 점유하지 않는다. Spring 테스트 위치는 `src/test/java/`이고 기존 `tests/`는 예약 폴더다.

## 라이브러리를 변경할 때

`build.gradle`을 수정한 작성자가 아래 명령으로 lock 파일을 갱신·검증하고 두 파일을 같은 PR에 포함한다.

```bash
./gradlew dependencies --write-locks
./gradlew build
```

팀원은 pull 후 평소대로 `./gradlew build`를 실행한다. 잠금 설정이 맞지 않을 때 임의로 `--write-locks`를 붙여 통과시키지 말고 변경 작성자와 설정을 확인한다.

Python용 uv 가상환경은 필요하지 않다. DB 테이블·업무 API는 다음 단계에서 추가하며 API 필드는 [contracts](../contracts/README.md)에 합의한다. 전체 설치 안내는 [로컬 개발 환경](../docs/infra/local-setup.md)을 참고한다.

[Spring Boot 시스템 요구사항](https://docs.spring.io/spring-boot/system-requirements.html) · [Gradle Wrapper](https://docs.gradle.org/current/userguide/gradle_wrapper_basics.html)

## Docker로 빌드·실행

Docker가 실행 중이면 호스트에 JDK·Gradle을 설치하지 않고도 빌드할 수 있다. 저장소 루트에서 실행한다. 처음에는 공식 이미지·Gradle·라이브러리를 내려받으므로 인터넷 연결이 필요하다.

```bash
docker build -t port8282-back:local ./back
docker run --rm --name port8282-back-local -p 127.0.0.1:8080:8080 port8282-back:local
```

브라우저에서 `http://127.0.0.1:8080/actuator/health`를 열어 `status: UP`을 확인한다. 종료는 실행한 터미널에서 Ctrl+C다. 호스트 8080이 사용 중이면 `-p 127.0.0.1:18080:8080`으로 바꾸고 18080으로 접속한다. Docker의 `EXPOSE`는 포트 설명이며 `-p`가 실제 호스트 연결을 만든다.

Dockerfile은 JDK 21 단계에서 Wrapper로 `build`를 실행해 테스트와 JAR 생성을 마친 뒤, JRE 21 실행 이미지로 JAR 하나만 복사한다. 실행 단계에는 Gradle·소스·개발 도구가 들어가지 않으며 UID/GID 10001로 실행한다. 기반 이미지는 확인한 다중 아키텍처 digest로 고정했고 OS 패키지는 이미지 빌드 시 설치한다. Mac 로컬 JDK의 패치 버전까지 같다는 뜻은 아니다.

Docker healthcheck는 30초마다 `/actuator/health` 응답을 확인한다. **단독 기본 실행의 local 프로필은 Spring 프로세스만 확인하고, Compose에서 사용하는 compose 프로필은 JDBC를 통한 DB 연결도 확인한다. AI·ML 연결이나 업무 기능 검증은 포함하지 않는다.** 배포 서버의 JVM 옵션은 필요할 때 `JAVA_TOOL_OPTIONS` 환경변수로 전달하며, 비밀번호는 Dockerfile이나 이미지에 넣지 않는다.

[Docker 다중 단계 빌드](https://docs.docker.com/build/building/multi-stage/) · [Temurin 공식 이미지](https://hub.docker.com/_/eclipse-temurin)

## Compose 개발 환경

저장소 루트의 공통·개발 Compose를 사용하면 호스트에 JDK를 설치하지 않아도 된다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

- Dockerfile의 `development` 단계를 사용하며 JDK 21, Gradle Wrapper, 소스·테스트를 포함한다. 실행 사용자는 UID/GID 10001, 작업 위치는 `/workspace`다.
- `bootRun`으로 실행한다. Compose Watch가 `back/src` 변경을 `/workspace/src`로 동기화하고 재시작하면 Gradle이 다시 컴파일한다. Java 파일은 컴파일이 필요하므로 Front의 화면 갱신처럼 즉각 반영되는 것은 아니다.
- Gradle 캐시는 `/home/app/.gradle`에 보관한다. 개발 설정에서 이 경로를 명명 볼륨으로 연결하면 컨테이너를 다시 만들어도 다운로드 캐시를 재사용한다.
- `build.gradle`, `gradle.lockfile`, Wrapper 설정 변경은 이미지를 다시 빌드한다. 의존성을 바꾼 작성자가 lock을 갱신·공유한다는 규칙은 같다.
- Compose 환경에서 테스트하려면 다음을 실행한다. 기존 HTTP 테스트는 `local` 프로필을 명시해 DB 없이 검사한다.

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec back ./gradlew --no-daemon test
```

프로필은 다음처럼 구분한다.

| 프로필 | 용도 | DB 상태 확인 |
| --- | --- | --- |
| `local` (기본) | DB 없는 단독 서버 실행·기본 HTTP 테스트 | 하지 않음 |
| `compose` | Compose에서 PostgreSQL과 연결 | JDBC 연결을 확인하며 DB 오류 시 전체 health가 실패 |

Compose는 `SPRING_PROFILES_ACTIVE=compose`, `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`를 전달한다. URL 예시는 `jdbc:postgresql://db:5432/port8282`이며 비밀번호는 이미지·Git에 포함하지 않는다. 기본 프로필의 DB 자동 구성을 제외한 것은 단독 실행 지원을 위한 설정이며, DB를 사용하는 환경에는 반드시 연결용 프로필을 적용한다.

`/actuator/health`는 상태만 표시한다. `compose` 프로필의 `/actuator/health/readiness`에도 DB 검사가 포함된다. 테이블·계약 데이터·migration·스케줄 계산·AI API는 아직 구현 전이며, JDBC health 성공은 업무 통합 성공과 다르다.
