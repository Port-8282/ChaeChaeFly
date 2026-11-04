# GitHub 보호 규칙 적용 안내

> 2026-11-04 · 설정 예정 안내. 현재 원격 저장소 설정·Jenkins 필수 검사는 적용하지 않았다.

## main

- PR을 통한 병합 필수.
- 작성자 외 Approve 4명 이상.
- 리뷰 대화 전부 해결 필수.
- 직접 push·force push·삭제 금지.
- 관리자·자동화 계정의 우회 권한도 제한.
- 같은 저장소의 dev에서 올라온 PR만 허용하는 별도 필수 검사.

## dev

- PR을 통한 병합 필수.
- 작성자 외 Approve 1명 이상.
- 직접 push·force push·삭제 금지.
- 리뷰 대화 해결도 필수로 설정하는 것을 권장.
- 일반 feature PR과 main → dev 이력 동기화 PR을 허용.

리뷰·대화 해결·우회 제한은 GitHub의 보호 규칙에서 설정한다. 적용 가능 범위는 저장소 공개 여부·사용 플랜에 따라 확인한다. 문서를 커밋하는 것만으로 보호 규칙이 활성화되지는 않는다. [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## main에 dev만 병합하도록 검사하기

PR을 요구하는 기본 보호 설정만으로 출발 브랜치까지 제한했다고 보지 않는다. Jenkins에 신뢰한 PR 출발점 검사를 구현하고 GitHub 필수 상태 검사로 연결한다.

main 대상 PR에서 아래 조건을 모두 확인한다.

1. PR 대상 저장소가 팀의 정해진 저장소인지.
2. PR 원본 저장소가 대상 저장소와 같은지. 외부 fork의 이름만 dev인 브랜치는 허용하지 않는다.
3. PR 원본 브랜치가 정확히 dev인지.
4. 검사 결과가 현재 PR head commit에 연결되는지. 새 커밋·PR 대상 변경 시 다시 검사한다.

이 검사는 PR 작성자가 수정한 Jenkinsfile의 조건문만으로 신뢰하지 않는다. Jenkins 관리자가 관리하는 검사 코드·신뢰한 설정으로 구현하고 PR 코드 실행에 운영 배포 자격증명을 제공하지 않는다. 검사 이름은 실제 연결 후 고정하고 필수 체크로 지정한다. 지금은 검사 구현 전이다.

## 병합 방법

- feature → dev: Squash and merge.
- dev → main: Create a merge commit.
- main → dev 동기화: Create a merge commit.
- main과 dev는 유지하고 완료된 feature만 삭제한다.
- 저장소에서 Merge commit과 Squash를 모두 허용한다. 이 정책과 충돌하는 선형 이력 강제 설정은 사용하지 않는다.

장기 유지 브랜치의 반복 Squash는 이미 병합한 커밋을 다음 PR에 다시 표시할 수 있다. 이력을 보존하는 배포·동기화 방법은 팀 적용안이다. [GitHub merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)

## Jenkins 연결

- feature → dev PR: 변경 서비스와 관련 API·통합 검사.
- dev 병합: 통합 검증. 개발 서버 자동 배포는 환경 확정 후 결정.
- dev → main PR: 현재 배포 후보의 전체 통합·호환 검사.
- main 병합: 검증된 운영 릴리스의 빌드·배포 절차. 자동 실행·별도 승인 여부는 아직 미정.
- 모델 출시: 승인된 main 기반 추론 코드와 검증된 모델 artifact 조합을 지정한다. 모델 출시도 공통 서버 배포 잠금을 사용한다.

기존 설계의 앱 서버 1대·6개 서비스는 유지한다. dev 브랜치 도입만으로 별도 개발 서버가 생기는 것은 아니다. main에 커밋이 있다는 것과 실제 서버 배포 성공도 구분한다.

## 템플릿과 적용 확인

기본 브랜치에 .github/pull_request_template.md와 .github/ISSUE_TEMPLATE의 Markdown 파일을 반영한다. 이 설계에서는 기본 브랜치를 main으로 사용한다. GitHub에서 새 PR을 작성하면 본문에 템플릿이 자동으로 표시되고 작성자가 내용을 채운다. 이미 작성한 PR은 자동 수정되지 않으며 제목은 컨벤션에 따라 직접 작성한다. 관련 작업은 GitHub Issue·PR 링크로 연결한다. CI는 Jenkins이므로 템플릿을 위해 .github/workflows를 추가할 필요는 없다. [GitHub PR 템플릿](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository), [Issue 템플릿](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)

자동 본문 입력과 규칙 강제는 별개다. 이 Markdown 파일은 양식을 제공하며 필수 항목 누락·제목 형식을 자동으로 막지 않는다. PR 승인·대화 해결·출발 브랜치 제한은 위 보호 설정과 필수 검사에서 처리한다.

설정 후에는 정상 feature → dev PR, 미승인 PR, 미해결 대화가 있는 main PR, 잘못된 출발 브랜치의 main PR, 정상 dev → main PR을 만들어 허용·차단 여부를 확인한다. 실제 main·dev에 시험용 직접 push를 실행하는 대신 보호 설정과 PR 동작으로 우선 검증한다.
