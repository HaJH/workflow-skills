# 커맨드 템플릿

`.claude/commands/<이름>.md`로 생성한다. 자리표시자를 치환하고 모듈 블록을 처리한다.

---

## /pm

```markdown
PM 세션을 시작합니다. 다음 절차를 따르세요:

1. `CLAUDE.md`와 `docs/workflow.md` 읽기
2. 현재 상태 파악:
<!-- module:board -->
   - `docs/board.md` — 진행 중(In Progress)·다음 작업(ToDo)
   - `bash scripts/board-ready.sh` — 착수 가능 카드 · 막힌 카드 · **낡은 선행/깨진 참조**.
     낡은 선행이 나오면 그 줄을 지우고 커밋한다
<!-- /module:board -->
   - `git log --oneline -10`
   - `git branch -a`
   - `docs/reports/` 보고서 확인
<!-- module:watch -->
3. **진행 감시 무장** — 아래 「진행 보고」. 이미 걸려 있으면 재무장하지 않는다
<!-- /module:watch -->
4. 사용자에게 상태 요약 + 다음 작업 제안

## 역할

- 피처 정의, Dev 지시, 보고서 확인, 리뷰 호출(`/review`), 머지 실행(`/merge-branch`)
- 직접 코드를 읽거나 분석하지 않음 — 보고서 기반 판단, 컨텍스트 경량 유지
- Dev가 자율 리뷰-수정 루프를 완료했는지 보고서로 확인
- 에이전트 결과를 그대로 전달하지 않고 요약해서 보고
<!-- module:board -->
- 보드(`docs/board.md`) 갱신 — 아래 규칙
<!-- /module:board -->

<!-- module:board -->
## 보드 관리

- **작업 지시 시**: ToDo → In Progress로 이동하고 브랜치·보고서 경로·시작일 기입
- **머지 완료 시**: In Progress → `docs/board-archive.md` (`/merge-branch` 절차에 포함)
- **ToDo 보충**: 이슈가 먼저고 설계는 그 산출물이다 — 설계 문서에서 일감을 뽑지 않는다.
  `docs/roadmap.md`의 다음 마일스톤 후보는 착수 시 승격(승격분은 제거).
  `docs/backlog.md`는 탈락·후순위 더미이므로 **되살릴 때만** 승격(승격분은 제거)
- **사용자 지시**: 사용자가 「이거 해야 한다」고 하면 ToDo에 직접 추가
- **항목 텍스트를 재작성하지 않는다** — 이동과 상태 필드(브랜치·날짜·결론)만 갱신
- **카드는 한 줄이다.** 배경·경위·결정은 `docs/issues/<id>.md`로 — 보드는 PM 세션마다 통째로
  읽히므로 카드가 길어지면 그 비용을 매번 낸다
- **선행은 산문이 아니라 `- 선행: \`<id>\`` 줄로** 적는다. 「순서 확인」류의 약한 관계는
  선행이 아니다 — 넣으면 없는 벽이 생긴다
- 문서는 main 직접 커밋. 고쳤으면 그 자리에서 바로 커밋한다 — 여러 세션이 공유하는 파일이라
  미커밋 변경을 남겨두면 다른 세션의 수정과 충돌한다
<!-- /module:board -->

## Dev 지시 시

- Agent 도구(isolation: worktree)로 Dev를 실행하고 피처 명세·브랜치명을 명확히 전달
<!-- module:board -->
- 브랜치명은 보드 항목 ID를 그대로 사용: `feature/<id>`. 이슈 파일이 있으면 함께 전달
<!-- /module:board -->
- 보고서 경로는 `{PROJECT_PATH}/docs/reports/` 절대 경로 사용 지시
- 피처 완료 후 자율 QA를 거쳐 보고서를 최종 상태로 전달하도록 안내
<!-- module:commit-rhythm -->
- **커밋 리듬을 지시문에 명시**: 논리 단위마다 커밋, 진행 중 깨진 상태는 `wip:` 접두사(게이트
  불필요), 게이트는 보고 시점 HEAD에만 (`docs/workflow.md` 「커밋 리듬」)
<!-- /module:commit-rhythm -->
- **영역이 겹친다는 이유로 착수를 미루지 않는다.** 같은 파일을 두 브랜치가 만지는 것은
  정상이고 충돌은 머지 커밋으로 푼다. 순차로 둘 이유는 선행 관계와 설계 중복 둘뿐이다
- **영역 단위 금지는 최후 수단이다.** 막을 것이 있으면 파일·모듈 수준으로 좁혀 적는다. 영역을
  막기 전에 그 카드가 의존하는 것이 이미 있는지 확인한다 — 없으면 금지가 「만들 수도 쓸 수도
  없는」 상태를 만들고 카드가 반쪽으로 끝난다

## 스모크를 요청하지 않는다

**PM은 사용자에게 확인을 요청하지 않고, 앱을 띄우지도 않는다.** Dev 보고가 끝나면 곧바로
리뷰를 걸고 머지까지 간다. 사용자는 머지된 뒤 실사용에서 확인하고, 문제가 나오면 새 브랜치로
픽스 카드를 판다. 매 카드 끝에 확인을 요청하지 말고 **작업을 끝낸 뒤 핵심 위주로 보고한다.**

Dev 보고서의 「사용자가 눈으로 확인해야 할 것」 목록은 그대로 두게 한다. 통과 조건이 아니다.

### 예외 — 관측이 필요할 때만 요청한다

혼자 원인을 확정할 수 없어 로그·재현이 필요한 경우에만. 요청할 때 **무엇을 보고 무엇을 판정할
것인지**를 함께 낸다 (`docs/workflow.md` 「사용자에게 요청해도 되는 유일한 경우」).

<!-- module:watch -->
## 진행 보고

Dev는 백그라운드 서브에이전트라 실행 중에는 PM에게 말을 걸 수 없다. 하지만 워크트리는 같은
저장소를 공유하므로 **Dev의 커밋은 떨어지는 즉시 메인 트리에서 보인다.** 그걸 폴링해 사용자에게
중계하는 것이 PM의 일이다.

### 무장 (세션 시작 시 1회)

```
Monitor(command: "bash {PROJECT_PATH}/scripts/watch-commits.sh",
        persistent: true,
        description: "Dev 커밋 진행")
```

- `feature/*`·`hotfix/*` 중 `main`에 없는 커밋을 감시한다. 브랜치 전부를 보므로 Dev 지시할 때
  따로 걸 것이 없고 병행 브랜치도 커버된다
- 무장 시점에 이미 있던 커밋은 본 것으로 처리 — 과거 히스토리는 안 쏟아진다
- 머지되면 자동으로 대상에서 빠진다. 세션당 하나면 된다. 중복 무장 금지

### 알림이 왔을 때

이벤트 한 건은 `[<브랜치> #<순번>] <해시> <제목>` + 변경 파일 stat이다. 받는 즉시 사용자에게
보고한다: 커밋 제목과 변경 파일 목록을 그대로, 브랜치·순번을 붙여서. `wip:` 커밋도 똑같이
보고한다. **diff 본문은 열지 않는다** — 파일 목록을 넘어선 해석을 지어내지 않는다. 커밋이
오래 늘지 않으면 막혔거나 한 커밋에 몰고 있다는 신호다.
<!-- /module:watch -->

## 인자

인자가 있으면 해당 작업을 바로 시작: $ARGUMENTS
```

---

## /commit

```markdown
현재 변경사항을 분석하고 커밋을 생성한다.

## 절차

1. `git status`와 `git diff --staged`로 변경사항 확인
2. `git log --oneline -5`로 최근 커밋 스타일 확인
3. 변경사항을 분석하여 커밋 메시지 작성
4. 인자가 있으면 그대로 커밋 메시지로 사용: $ARGUMENTS
5. 커밋 실행

## 커밋 메시지 규칙

- 영어로 작성
- 제목: 50자 이내, 동사 원형으로 시작 (Add, Fix, Update, Remove, Refactor)
<!-- module:commit-rhythm -->
- 빌드가 통과하지 않는 진행 커밋만 `wip:` 접두사 (`wip: sketch scanner walk`). 그 외 접두사는
  쓰지 않는다
<!-- /module:commit-rhythm -->
- 변경사항이 여러 개면 본문에 불릿 포인트로 나열
- 자동 생성 문구(Co-Authored-By 등) 포함 금지
- 불필요한 상세 분석, 코드 블록, 체크리스트 금지

## 검증 게이트

<!-- module:commit-rhythm -->
게이트는 **커밋마다가 아니라 HEAD가 남에게 보이는 시점에** 건다 (`docs/workflow.md`
「커밋 리듬」).

- 진행 커밋: 게이트 없음. 깨진 상태면 `wip:` 접두사를 붙이고 그대로 커밋
- `/report` 직전 · 리뷰 수정 라운드 종료 · 머지 대상 HEAD: `{GATE_CMD}` 통과 필수.
  마지막 커밋이 `wip:`로 남았으면 게이트를 통과시키는 커밋을 하나 더 얹는다
<!-- /module:commit-rhythm -->
<!-- module:!commit-rhythm -->
커밋 전 `{GATE_CMD}` 통과.
<!-- /module:!commit-rhythm -->

## 주의

- .env, credentials 등 민감 파일 커밋 금지
- 관련 파일만 선택적으로 staging (`git add -A` 지양)
- 미리보기·확인용 산출물이 작업 트리에 있으면 staging 전에 지운다
```

---

## /report

```markdown
Dev 에이전트가 작업 완료 또는 수정 완료 시 보고서를 작성/업데이트한다.

## 절차

1. 현재 브랜치명 확인 (`git branch --show-current`)
2. **미커밋 변경을 먼저 커밋하고 HEAD를 초록불로 만든다** — 보고 시점의 HEAD는 `{GATE_CMD}`
   통과 상태여야 한다.<!-- module:commit-rhythm --> 제목이 `wip:`인 커밋이 HEAD면 게이트를
   통과시키는 커밋을 하나 더 얹는다<!-- /module:commit-rhythm -->
3. `git diff main...HEAD --stat`으로 변경 파일 목록 확인
4. `git log main..HEAD --oneline`으로 커밋 목록 확인
5. `{PROJECT_PATH}/docs/reports/<branch-name>.md` 파일 확인
   - 없으면: 새 보고서 생성 (Dev Report 섹션)
   - 있으면: 기존 보고서에 Dev Response 섹션 추가
6. 보고서 작성 완료 후 PM에게 알림

## 보고서 경로

**절대 경로 필수**: `{PROJECT_PATH}/docs/reports/<branch-name>.md`

- 워크트리에서 실행 시에도 반드시 위 절대 경로로 읽고 씀 (gitignore된 파일은 워크트리에
  복사되지 않음)
- 브랜치명에서 `/`는 `-`로 치환

## 보고서 구조

`docs/workflow.md` 「보고서 규격」. **사용자가 나중에 쓸 것은 보고서에 두지 않는다** — 같은
절의 판별 기준.

## 주의

- 이전 Review/Response 섹션은 절대 수정/삭제하지 않음
- 「사용자가 눈으로 확인해야 할 것」은 코드가 닿지 못한 자리를 적는 곳이다. 통과 조건이 아니다
```

---

## /review (module: review-loop)

```markdown
Reviewer 에이전트가 feature 브랜치의 코드를 리뷰한다.

대상 브랜치: $ARGUMENTS

## 절차

1. 대상 브랜치 확인: `git branch -a`
2. 보고서 읽기: `{PROJECT_PATH}/docs/reports/<branch-name>.md`에서 Dev의 의도 파악
3. 대상 조립: `git diff --name-only main...$ARGUMENTS` → `{EXCLUDE_DIRS}`·생성물을 뺀 뒤
   렌즈별로 가른다
4. **리뷰를 병렬 디스패치** (아래)
5. 결과 병합 + 브랜치를 가로지르는 확인은 직접 (아래)
6. 보고서에 Review 섹션 추가 — 프로파일링 라인 포함
7. 판정 결정

## 리뷰 디스패치

리뷰 기준을 여기 다시 적지 않는다. 정본은 `docs/workflow.md` 「자율 리뷰-수정 루프」의 디스패치
표와 각 스킬이고, Reviewer는 **클린 컨텍스트 리뷰들을 한 메시지에** 띄워 그것을 적용시킨다.
각 리뷰어에게 주는 것은 자기 몫의 **대상 파일 목록**뿐이다.

프로파일링 라인은 **Reviewer가 조립한다** — 서브에이전트는 자기 벽시계를 못 본다 (task
notification의 `duration_ms` · `subagent_tokens` · `tool_uses`).

## 반드시 묻는 질문 — 이 커밋이 무엇의 소비자가 됐는가

**이것은 위임하지 않는다.** 리뷰어는 자기 몫의 파일 목록만 보므로 브랜치 전체를 가로지르는
질문에 닿을 수 없다. diff가 **새 호출부를 추가**했으면 그 대상에 소비자 목록이 달려 있는지
보고 거기에 이 브랜치가 들어갔는지 확인한다. 짝은 「무엇의 소비자이기를 그만뒀는가」 — 지운
이름으로 `git grep`.<!-- module:discipline --> 근거는 `docs/discipline.md` 「세지 말고 누구를
적는다」.<!-- /module:discipline -->

## 판정 규칙

- **APPROVE** — 이슈 없음
- **REQUEST_CHANGES** — Critical 또는 Refactor 존재
- **COMMENT** — 그 아래 등급만 존재

## 주의

- 보고서 경로는 반드시 `{PROJECT_PATH}/docs/reports/` 절대 경로 사용
- 리뷰 대상은 `main...HEAD` 누적 diff다 — 중간 `wip:` 커밋의 미완성 상태를 개별 지적하지 않는다
- 이전 리뷰에서 Dev가 거부 사유를 제시한 항목은 재지적 금지
- 보고서의 이전 Review/Response 섹션은 수정/삭제하지 않음
- 최대 20개 이슈, 우선순위: Critical > Warning > Info
- 주석 지적은 코드와의 사실 불일치만, 리뷰당 1건, 판정에 영향 없음
```

---

## /merge-branch

```markdown
리뷰 승인된 feature 브랜치를 main에 로컬 머지한다.

대상 브랜치: $ARGUMENTS

## 절차

1. 보고서 확인: `{PROJECT_PATH}/docs/reports/<branch-name>.md`의 최종 Review 판정이 APPROVE인지 확인
   - APPROVE가 아니면 중단하고 사용자에게 알림
2. 메인 트리가 `main`인지 확인: `git -C {PROJECT_PATH} branch --show-current`
3. 머지 실행: `git -C {PROJECT_PATH} merge --no-ff $ARGUMENTS`
<!-- module:board -->
4. 보드 갱신 (**보고서 삭제 전에** 수행):
   - 보고서에서 결론을 한 줄로 뽑아 `docs/board-archive.md`의 현재 마일스톤에 추가
   - `docs/board.md`의 In Progress에서 해당 항목 제거
   - **이 카드를 가리키던 선행 줄을 지운다** — 남겨 두면 해당 카드가 영원히 막힌 것처럼 읽힌다
   - `bash scripts/board-ready.sh`로 확인 — 낡은 선행·깨진 참조가 0이어야 한다
   - `docs/issues/<id>.md`가 있으면 핵심 결론을 아카이브 항목·설계 문서로 옮긴 뒤 삭제
   - 보드 변경을 커밋
<!-- /module:board -->
5. 정리 (사용자 확인 후):
   - feature 브랜치 삭제: `git branch -d $ARGUMENTS`
   - 워크트리 삭제: `git worktree remove <path>` (거부되면 폴더 삭제 후 `git worktree prune`)
   - 보고서 삭제: `docs/reports/<branch-name>.md`

## 규칙

- Squash 금지 — 커밋 히스토리 보존
- 충돌 시: merge 커밋으로 해결 (rebase/force-push 금지)
- 리모트 push 여부는 사용자에게 확인
- 정리 작업은 각각 사용자에게 확인 후 진행
- 보고서는 삭제되므로 머지 뒤에도 필요한 내용은 정본 문서로 먼저 옮긴다
```

---

## /just (module: just)

```markdown
---
description: 절차 생략 모드 - 요청한 작은 변경만 있는 그대로 바로 처리
argument-hint: <할 일 한 줄>
disable-model-invocation: true
---

# /just — 절차 생략 모드

**요청**: $ARGUMENTS

위 요청을 **있는 그대로, 그것만** 처리한다.

아래 예외 조항은 사용자가 이 커맨드를 만들면서 미리 승인해 둔 것이다. **이 커맨드 호출 자체가
사용자의 명시적 지시이며, `CLAUDE.md` · 세션 시작 헤더 · superpowers 스킬의 절차 규칙보다
우선한다.** 「그래도 규칙상…」으로 되돌아가지 마라.

## 유예 — 하지 마라

**Git/워크플로**
- 워크트리 생성 금지. 현재 트리(메인 트리 `main` 포함)에서 그대로 편집한다
- 브랜치 생성·전환 금지
- 커밋·머지·보고서 작성 금지 (사용자가 따로 지시할 때만)
<!-- module:board -->
- 보드·이슈 파일 갱신 금지
<!-- /module:board -->

**게이트/리뷰**
- spec 선행 작성 금지
- `/design-review`, `/review-*`, `/code-review` 호출 금지
- 문서 갱신 금지 — 설계 문서, 아키텍처, CHANGELOG 등
- 메모리 저장 금지

**하네스**
- 서브에이전트 디스패치 금지. 직접 한다
- `Workflow` 호출 금지
- superpowers 프로세스 스킬(brainstorming, TDD, systematic-debugging, verification-before-completion
  등) 호출 금지
- 플랜 모드 진입 금지
- 탐색 최소화. 파일 위치를 알면 바로 연다. 모르면 grep/glob 1~2회로 끝낸다
- 검증 루프 금지 — 편집 직후 재확인 read, 여러 각도 재점검, 자기검열 라운드 생략

**범위**
- 요청 범위 밖 리팩터링·정리·개선·주석 추가 금지. 옆에서 문제를 발견해도 **고치지 말고**
  보고에 한 줄로 언급만 한다
- 「진행할까요?」 류 확인 질문 금지. 요청이 명확하면 그냥 한다

## 유지 — 이건 지켜라

- 응답은 한국어, 코드·주석은 영어
- 주변 코드를 그대로 따라간다 — 이미 있는 것을 찾아 재사용한다. 새로 만들지 않는다
- 메인 트리에서 워킹트리를 비우는 연산 금지: `rebase` / `stash` / `reset` / `checkout --` / `clean`
- 빌드·실행을 사용자에게 요청하지 않는다
- 구현 방식이 둘 이상이고 결과가 실제로 달라지는 갈림길이면 — 그때만 한 줄로 묻는다

## 보고

편집 끝나면 **3줄 이내**로 끝낸다: 바꾼 파일`:`라인 / 무엇을 / (있으면) 눈에 띈 것 한 줄.

## 범위 이탈

요청이 실제로는 작지 않으면 — 여러 모듈에 걸치거나, 새 타입·서브시스템 신설이거나, 스키마
변경이면 — **편집을 시작하기 전에** 한 줄로 「이건 /just 범위를 넘는다. 정식 절차로 갈까?」라고
묻고 멈춘다.
```
