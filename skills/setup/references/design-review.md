# 설계 검토 게이트 (module: design-review)

구현 전에 spec의 코드 구조 설계를 클린 컨텍스트 파이프라인(추출 → 검증 → 판정)으로 검수한다.
언어 무관. 생성 파일:

| 대상 | 원본 | 치환 |
|---|---|---|
| `.claude/skills/design-review/SKILL.md` | `design-review/SKILL.md` | `{PROJECT_PATH}` · `{SOURCE_DIRS}` |
| `.claude/skills/design-review/prompts/round-1.md` | `design-review/prompts/round-1.md` | `{PROJECT_PATH}` |
| `.claude/skills/design-review/prompts/re-review.md` | `design-review/prompts/re-review.md` | `{PROJECT_PATH}` |
| `.claude/agents/design-claim-extractor.md` | `design-review/agents/design-claim-extractor.md` | 없음 |
| `.claude/agents/design-fact-verifier.md` | `design-review/agents/design-fact-verifier.md` | `{SOURCE_DIRS}` |
| `.claude/agents/design-structure-judge.md` | `design-review/agents/design-structure-judge.md` | 없음 |
| `docs/design-constitution.md` | `design-review/design-constitution.md` | 프로젝트 고유 조항은 사용자와 함께 추가 |
| `docs/specs/` | 빈 디렉터리 + `.gitkeep` | — |
| `.gitignore` | `docs/specs/.review-cache/` 추가 | — |

spec 파일명은 `docs/specs/YYYY-MM-DD-<topic>.md`. superpowers의 brainstorming이 쓰는 경로
(`docs/superpowers/specs/`)와 다르므로, 프로젝트가 superpowers를 쓰면 CLAUDE.md에 「spec 위치는
`docs/specs/`」 한 줄을 둔다.

## 셋업 시 확인할 것

- 설계 헌법의 프로젝트 고유 조항 — 골격의 조항은 일반 원칙이다. 프로젝트의 레이어 규칙(예: 「core
  크레이트는 UI 무지」)이 있으면 조항으로 추가한다. 번호는 골격 뒤에 이어서
- 「의존 방향」 조항의 정본 — 모듈 의존을 선언하는 파일(`Cargo.toml` 워크스페이스, `package.json`,
  `.Build.cs`)이 있으면 그 이름을 적는다

## 유지 규칙

- 조항 번호는 불변, 추가만. spec·리뷰가 번호로 참조한다
- 파이프라인 티어는 각 에이전트의 frontmatter가 정한다. 바꾸려면 거기서
- 라운드마다 프로파일링 블록을 낸다. 스킬에 기준값을 박지 않는다
