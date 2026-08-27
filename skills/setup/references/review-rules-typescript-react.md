# TypeScript React Review Rules (Addon)

`review-rules-typescript.md`에 덧붙여 쓴다. Severity 정의는 base와 같다. 린터가 켜 둔 React 룰
(`rules-of-hooks` 등)은 findings로 쓰지 않는다.

## REACT: React Correctness

**Critical:** effect로 파생 상태 계산 (렌더 중 계산이나 `useMemo` 대상), 이벤트에 속한 로직을
effect로 처리, stale closure가 실동작을 바꾸는 경우, 재정렬되는 리스트의 index key
**Warning:** 스토어 전체 구독 — 셀렉터 없이 `useXxxStore()`를 부르면 모든 변경에 리렌더, 로컬 state가
스토어와 같은 사실의 중복 소스, memo된 자식에 매 렌더 새 객체/배열/함수 identity 전달, effect 의존성
누락·과잉, 컴포넌트 파일의 비컴포넌트 export — Fast Refresh가 깨진다 (상수·헬퍼·variant 레시피는
별도 파일로)
**Info:** 성능 근거 없는 `useMemo`/`useCallback`

## STORE: Stores & Surfaces

**Critical:** 스토어 필드의 표면 소유 위반 — 오류·상태 필드 하나를 서로 다른 라우트·표면이 그리면
표면별 필드로 분리할 것. **「라우트 진입 시 클리어」는 해소가 아니다** — 잘못된 표면에 도달하는
것 자체는 두고 타이밍으로 가릴 뿐이라 두 표면이 동시 마운트되는 구성에서 재발한다
**Warning:** 컴포넌트에서 백엔드 이벤트 직접 구독 — 스토어의 연결 함수(앱 시작 시 1회, teardown
반환)를 통할 것. 마운트마다 재구독하면 리스너가 증식한다, 액션 성공 시 자기 오류 필드 미클리어,
라우트 컴포넌트에 비즈니스 로직 매몰 → 스토어/`lib/`, 스토어 간 직접 결합
**Info:** 스타일 클래스 조합 중복

## P: 프로젝트 고유

(셋업 시 채운다. 운영/구성 경계 같은 UI 소유 규칙이 있으면 정본 문서(`docs/design/ui-map.md` 등)를
가리키는 항목으로)
