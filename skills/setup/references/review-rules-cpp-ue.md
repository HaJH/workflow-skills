# C++ Unreal Engine Review Rules (Addon)

`review-rules-cpp.md`에 덧붙여 쓴다. Severity 정의는 base와 같다. **P** 항목의 정본은 프로젝트
코딩 규칙 문서다.

## NC-UE: UE Naming Conventions

**Warning:** 클래스/구조체 UE 접두사 누락 (A/U/F/I/E/T/S), 파일명에 타입 접두사 포함
**Info:** Blueprint 노출 함수명이 BP 사용자 관점에서 불명확

## FMT-UE: Formatting

**Critical:** **P** C++ 소스의 장식적 비ASCII 문자(`—` `–` `→` `§`) — BOM 없는 파일을 MSVC가
cp949로 해석해 컴파일 파손. 한글 주석 자체는 허용
**Critical:** 블록 주석 본문의 `*/` 시퀀스 — 주석이 거기서 끝나 뒤 텍스트가 코드로 해석됨

**Check pattern**: 코드·주석 전체를 비ASCII로 스캔(한글 제외). `/* … */` 구간 안의 `*/`.

## UE: Unreal Engine Specific

**Critical:** 싱글플레이 프로젝트의 리플리케이션 코드 (`Replicated`, `Server`, `Client`, `NetMulticast`)
**Warning:** UObject 멤버에 `UPROPERTY()` 누락 (GC 미추적), Blueprint 함수에 `Category` 누락,
생성자/소멸자에서 가상 함수 호출, 문자열 리터럴에 `TEXT()` 누락
**Info:** 불필요한 Tick 활성화

## R-UE: UE Resource Management

**Critical:** 에셋 직접 로드 (레지스트리/GameData 패턴 사용), `NewObject`/`CreateDefaultSubobject`의
잘못된 Outer, 인터페이스 raw 포인터를 멤버로 보관 (GC 추적 불가 — 액터로 보관)
**Warning:** 게임플레이 코드(Tick·Notify·어빌리티)에서 `LoadSynchronous()`를 정상 경로로 사용 —
하드 레퍼런스 또는 프리로드. `Get()` 실패 후 폴백은 허용, 에디터 전용 코드는 예외

## GAS: Gameplay Ability System (해당 시)

**Critical:** Raw GAS 패턴 직접 사용 (래퍼 경유 필수), GameplayTag 하드코딩
**Warning:** AbilitySystemComponent 직접 접근 (서브시스템/인터페이스 경유)

## IF: Interface & Casting

**Warning:** **P** `Cast<ConcreteClass>` / `Cast<IInterface>` — 프로젝트의 인터페이스 헬퍼 경유.
건드린 함수 전체에서 본다, 바뀐 줄만이 아니라

## MOD-UE: Module Dependencies

**Critical:** 순환 의존, `.Build.cs`에 미등록된 모듈 `#include`
**Warning:** 단방향 의존성 흐름 위반, 불필요한 모듈 의존 추가

**Check pattern**: 파일 경로에서 모듈(`Source/<Module>/`)을 잡고 그 `.Build.cs`의
`Public/PrivateDependencyModuleNames`를 읽는다 — **`.Build.cs`가 정본**이고 아키텍처 문서는 개요다.
