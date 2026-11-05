# Jenkins CI

**팀 공통 검사 환경입니다. 현재 배포 기능은 없습니다.** 설치와 GitHub 연결은 [Jenkins CI 안내](../../docs/infra/ci.md)를 따릅니다.

```text
GitHub PR·브랜치 변경
        ↓
Controller: 작업 예약·결과 표시 (executor 0)
        ↓
Agent: 설정 검사·테스트·이미지 빌드 (executor 1)
        ↓
CI 전용 Docker: 임시 실행·기본 응답 확인
        ↓
결과 보관·이번 검사 자원 정리
```

Controller·Agent·CI Docker는 앱의 6개 서비스와 별도 Compose로 실행합니다. 호스트 Docker socket이나 앱 DB 볼륨은 Agent에 연결하지 않습니다. DinD는 privileged 권한을 사용하므로 신뢰한 팀 코드만 실행하며, 외부 fork PR 자동 실행은 구성하지 않습니다.

Jenkinsfile과 검사 명령은 준비했지만 GitHub Credentials·Multibranch 연결·필수 상태 검사는 관리자 설정이 필요합니다. 저장소에 파일을 올리는 것만으로 자동 활성화되지는 않습니다. [GitHub 보호 규칙](../../docs/infra/github-rules.md)

Jenkins 상태 볼륨은 삭제·재생성 후에도 설정을 보관하는 용도입니다. 별도 백업을 대신하지 않습니다. 운영 배포·모델 출시·Registry·SSH 권한은 이후 CD 단계에서 별도 설계합니다.
