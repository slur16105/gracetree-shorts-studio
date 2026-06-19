---
title: 'Karpathy식 원칙을 적용한 AGENTS.md'
type: 'chore'
created: '2026-06-19'
status: 'done'
baseline_commit: 'd2e9d64ac250a3be23ea64f7d865d2070c25601b'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 저장소 루트에 `AGENTS.md`가 없어 코딩 에이전트가 작업 범위, 변경 안전성, 검증 수준과 프로젝트 문서 우선순위를 일관되게 판단할 공통 지침이 없다. AI가 코드를 빠르게 생성하더라도 과도한 추상화, 관련 없는 변경, 검증되지 않은 완료 보고를 방지할 최소 규칙이 필요하다.

**Approach:** Andrej Karpathy가 AI 코딩에 관해 강조한 인간 감독, 점진적 작업, 생성 코드의 비대화·취약한 추상화 경계라는 관점을 참고하되, 특정 발언을 공식 표준처럼 복제하지 않는다. 이를 GraceTree 저장소에서 실행 가능한 짧은 명령형 규칙으로 변환하고, 상세 아키텍처는 기존 문서에 위임한다.

## Boundaries & Constraints

**Always:**

- 작업 전에 사용자 요청, 관련 파일, 기존 테스트와 가까운 구현 패턴을 먼저 읽는다.
- 가장 작은 완전한 변경으로 요청을 충족하고 기존 구조와 명명을 재사용한다.
- 사실, 추론, 가정을 구분하고 불확실성이 결과를 바꾸면 사용자에게 확인한다.
- 입력 파일, 기존 결과, 사용자 변경과 작업 트리의 관련 없는 변경을 보존한다.
- 변경된 동작을 위험도에 비례해 테스트하고 실제 명령 결과를 확인한다.
- 완료 보고에는 변경 파일, 검증 명령, 미검증 항목을 정확히 명시한다.
- PRD, Architecture, Epics, 승인된 Story와 Sprint Change Proposal의 범위를 준수한다.

**Ask First:**

- 요구사항 또는 승인된 Story 범위를 확대하는 기능 추가
- 아키텍처 결정, 공개 계약, DB 스키마 소유권 또는 기술 스택 변경
- 파괴적 명령, 데이터 삭제, 기존 결과 교체, 외부 시스템 변경
- 실패하는 테스트를 삭제·완화하거나 검증 기준을 낮추는 조치

**Never:**

- 요청하지 않은 리팩터링, 추상화, 의존성 또는 호환 계층을 추가하지 않는다.
- 오류를 숨기거나 임시 우회로를 정상 해결로 보고하지 않는다.
- 테스트를 통과시키기 위해 제품 동작이나 테스트 의미를 왜곡하지 않는다.
- 읽지 않은 파일, 실행하지 않은 테스트 또는 확인하지 않은 결과를 확인했다고 주장하지 않는다.
- 사용자 변경을 되돌리거나 전체 문서를 재생성해 국소 변경을 덮어쓰지 않는다.
- 비밀값, 개인 데이터, 입력 미디어 내용을 로그·문서·외부 서비스에 노출하지 않는다.

</frozen-after-approval>

## Code Map

- `AGENTS.md` -- 모든 코딩 에이전트가 저장소 작업 시 적용할 루트 지침
- `_bmad-output/planning-artifacts/architecture.md` -- 기술 결정, 경계, 명명 및 테스트 규칙의 상세 기준
- `_bmad-output/planning-artifacts/epics.md` -- 승인된 Epic·Story 범위와 인수 조건
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-19.md` -- 승인된 국소 변경과 범위 제한 사례

## Tasks & Acceptance

**Execution:**

- [x] `AGENTS.md` -- 짧고 명령형인 저장소 지침을 작성하고 상세 프로젝트 계약은 기존 BMad 산출물로 연결한다.
- [x] `AGENTS.md` -- 작업 전 이해, 최소 변경, 가정 관리, 테스트·검증, 안전, 완료 보고 규칙을 구분해 스캔 가능하게 구성한다.
- [x] `AGENTS.md` -- 현재 작업 트리의 기존 변경을 보존하며 새 파일만 추가한다.

**Acceptance Criteria:**

- Given 저장소를 처음 연 코딩 에이전트가 있을 때, when `AGENTS.md`를 읽으면, then 작업 전 확인 사항과 수정·검증·보고 기준을 추가 설명 없이 이해할 수 있다.
- Given 국소 수정 요청이 있을 때, when 지침을 적용하면, then 관련 없는 리팩터링과 전체 문서 재생성을 금지하고 최소 변경을 요구한다.
- Given 위험하거나 범위가 확대되는 결정이 있을 때, when 지침을 적용하면, then 에이전트가 임의 진행하지 않고 사용자 승인을 요청한다.
- Given 구현을 완료했다고 보고할 때, when 검증 결과를 정리하면, then 실행한 검사와 실행하지 못한 검사를 구분한다.
- Given Architecture 또는 Story와 `AGENTS.md`가 충돌할 때, when 우선순위를 판단하면, then 사용자 지시와 승인된 프로젝트 산출물을 우선하고 충돌을 보고한다.

## Spec Change Log

- 2026-06-19 리뷰: 승인 상태가 없는 산출물의 권위 오인, 안전 규칙 우선순위, 재생성 예외, dirty baseline, 고위험 변경 검증, 민감정보 문서 노출, 호환 계층 및 완료 보고 재현성 문제를 확인했다. `AGENTS.md`에 명시적 guard를 추가하고 검증 명령을 baseline commit 기준으로 변경했다. 기존의 최소 변경·인간 승인·검증 중심 구조와 100줄 이하 문서 목표는 유지했다.

## Design Notes

- `AGENTS.md`는 프로젝트 백과사전이 아니라 작업 행동 계약으로 유지한다.
- Karpathy의 “vibe coding” 묘사를 그대로 권장하지 않는다. 생성 속도는 활용하되, 비대화·복사 반복·취약한 추상화를 인간 감독과 검증으로 통제하는 방향만 채택한다.
- 세부 기술 버전, 디렉터리 전체 구조와 모든 테스트 명령은 Architecture 또는 향후 `project-context.md`가 소유한다.
- 중복과 컨텍스트 팽창을 피하기 위해 문서는 약 100줄 이하를 목표로 한다.

## Verification

**Commands:**

- `git diff --check d2e9d64ac250a3be23ea64f7d865d2070c25601b -- AGENTS.md` -- expected: 공백 오류 없음
- `git diff d2e9d64ac250a3be23ea64f7d865d2070c25601b -- AGENTS.md` -- expected: `AGENTS.md` 추가와 승인된 리뷰 수정만 포함
- `rg -n '^#|^##|^- ' AGENTS.md` -- expected: 핵심 규칙이 짧은 섹션과 명령형 목록으로 확인됨

**Manual checks:**

- 규칙이 구체적이고 검증 가능하며 Architecture·Epics와 충돌하지 않는지 확인한다.
- Karpathy 관련 내용이 직접 인용이나 권위 호소가 아니라 프로젝트용 실행 규칙으로 재구성됐는지 확인한다.

## Suggested Review Order

**문서 권위와 범위**

- 승인 상태가 있는 산출물만 구현 계약으로 사용한다.
  [`AGENTS.md:5`](../../AGENTS.md#L5)

- 안전 최소선은 상위 문서와 충돌해도 자동 완화되지 않는다.
  [`AGENTS.md:12`](../../AGENTS.md#L12)

**변경 안전성**

- baseline과 전체 작업 트리 상태로 사용자 변경을 분리한다.
  [`AGENTS.md:25`](../../AGENTS.md#L25)

- 재생성·입력 교체의 허용 경계를 원자적 안전 조건으로 제한한다.
  [`AGENTS.md:44`](../../AGENTS.md#L44)

**검증과 완료**

- 고위험 변경 유형별 최소 검증 계층을 명시한다.
  [`AGENTS.md:63`](../../AGENTS.md#L63)

- 완료 보고는 실행 명령과 미검증 위험까지 재현 가능하게 남긴다.
  [`AGENTS.md:73`](../../AGENTS.md#L73)
