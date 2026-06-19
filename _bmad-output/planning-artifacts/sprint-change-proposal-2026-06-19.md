---
project: gracetree-shorts-studio
date: 2026-06-19
status: approved-and-applied
change_scope: minor
source: implementation-readiness-report-2026-06-19.md
approved_at: 2026-06-19
---

# Sprint Change Proposal

## 1. 이슈 요약

구현 준비성 검사에서 `epics.md`의 세 스토리에 구현 해석이 갈릴 수 있는 공백이 확인됐다.

- Story 1.4가 최초 사용하는 `job_inputs` 스키마의 생성 소유권이 없다.
- Story 1.7이 최초 사용하는 `resources` 스키마의 생성 소유권이 없다.
- Story 2.1의 실제 엔진 수직 슬라이스가 완료 시 생성해야 하는 검증 가능한 산출물이 없다.

근거는 `implementation-readiness-report-2026-06-19.md`의 주요 이슈 1·2와 우선 권고 작업 1~3이다. 보고서는 전체 Epic 재작성이 아니라 세 Story의 국소 보정을 요구한다.

## 2. 영향 분석

### Epic 영향

- Epic 1과 Epic 2의 사용자 가치, 범위, 순서 및 FR 커버리지는 유지된다.
- Epic 추가·삭제·재정의·재정렬은 필요 없다.
- Epic 3과 Epic 4에는 영향이 없다.

### Story 영향

- Story 1.4: `job_inputs` 순차 마이그레이션의 최초 소유권과 검증 조건 추가
- Story 1.7: `resources` 순차 마이그레이션의 최초 소유권과 검증 조건 추가
- Story 2.1: 라이선스 안전 샘플로 생성하는 최소 MP4 진단 산출물과 완료 검증 추가
- 그 외 Story는 변경하지 않는다.

### 산출물 충돌

- PRD: 기능·MVP 범위 변경 없음
- Architecture: 기존 SQLite 명명 규칙, 순차 마이그레이션, 라이선스 안전 샘플, FFmpeg 검증 규칙과 일치
- UX: Story 2.1에서 진단 산출물 완료 상태를 표시하는 문구만 기존 진행·완료 패턴 안에서 사용하며 화면 구조 변경 없음
- Sprint status: Epic·Story 추가, 삭제, 번호 변경이 없으므로 변경 불필요

### 기술 영향

- 구현자는 각 테이블을 최초 필요 시점에 생성할 수 있다.
- 마이그레이션 테스트는 빈 DB와 직전 스키마 DB를 대상으로 수행한다.
- Story 2.1 완료 판정은 프로토콜 이벤트만이 아니라 실제 MP4 파일 검증까지 포함한다.

## 3. 권고 접근

**선택: Direct Adjustment**

- 작업량: 낮음
- 위험: 낮음
- 일정 영향: 무시 가능한 수준
- 롤백: 불필요
- MVP 재검토: 불필요

세 스토리의 인수 조건만 추가하면 준비성 보고서의 주요 이슈를 직접 해소할 수 있다. 전체 Epic 재생성이나 PRD·아키텍처 변경은 범위를 불필요하게 확대한다.

## 4. 상세 변경 제안

### Story 1.4 — Acceptance Criteria

**OLD**

입력 메타데이터 저장은 요구하지만 `job_inputs` 스키마 생성 시점과 구조를 지정하지 않는다.

**NEW**

```markdown
**Given** Story 1.3까지의 스키마가 적용된 데이터베이스가 있을 때
**When** 이 스토리의 순차 마이그레이션을 적용하면
**Then** `job_inputs` 테이블에 `id`, `job_id`, `role`, `original_name`, `managed_path`, `status`, `created_at`, `updated_at` 열을 추가한다.
**And** `job_id`는 `jobs.id`를 참조하며 작업 삭제 시 입력 메타데이터도 삭제되는 외래 키 제약을 적용한다.
**And** 동일 작업에서 같은 관리 경로가 중복 기록되지 않도록 `uq_job_inputs_job_id_managed_path` 유일 제약을 적용하고 `idx_job_inputs_job_id` 인덱스를 생성한다.
**And** 빈 DB와 Story 1.3 스키마 DB 모두에서 순차 적용과 중복 적용 방지 검증이 성공한다.
```

**근거:** 입력 등록 기능이 최초 사용하는 테이블의 소유권, 제약 및 검증 기준을 구현 전에 고정한다.

### Story 1.7 — Acceptance Criteria

**OLD**

공통 리소스 메타데이터 저장은 요구하지만 `resources` 스키마 생성 시점과 구조를 지정하지 않는다.

**NEW**

```markdown
**Given** Story 1.6까지의 스키마가 적용된 데이터베이스가 있을 때
**When** 이 스토리의 순차 마이그레이션을 적용하면
**Then** `resources` 테이블에 `id`, `resource_type`, `original_name`, `managed_path`, `status`, `created_at`, `updated_at` 열을 추가한다.
**And** `resource_type`은 지원하는 공통 리소스 종류만 허용하고 `uq_resources_resource_type` 유일 제약으로 종류별 활성 메타데이터를 하나만 저장한다.
**And** 상태 조회를 위한 `idx_resources_status` 인덱스를 생성한다.
**And** 빈 DB와 Story 1.6 스키마 DB 모두에서 마이그레이션과 기존 작업 데이터 보존 검증이 성공한다.
```

**근거:** 공통 리소스 기능이 최초 사용하는 테이블의 소유권, 데이터 무결성 및 조회 기준을 고정한다.

### Story 2.1 — Acceptance Criteria

**OLD**

`start → stage_started → progress → completed` 흐름은 요구하지만 `completed`를 입증하는 파일 산출물이 없다.

**NEW**

```markdown
**Given** 라이선스 안전 고정 샘플로 생성 시도가 실행 중일 때
**When** 엔진이 최소 생성 흐름을 끝까지 처리하면
**Then** 작업의 `temp/attempts/<attemptId>/vertical-slice.mp4`에 짧은 MP4 진단 산출물을 생성한다.
**And** 산출물은 0바이트가 아니고 `ffprobe`로 영상 스트림과 0초보다 긴 재생 시간을 확인할 수 있어야 한다.
**And** 파일 검증이 성공한 뒤에만 `completed` 이벤트와 100% 진행률을 발행하고 UI에 `샘플 생성 완료`와 산출물 파일명을 표시한다.
```

**근거:** 프로토콜 스텁이 아니라 실제 엔진·FFmpeg 경계를 통과하는 최소 수직 슬라이스임을 검증한다.

## 5. 체크리스트 결과

- [x] 1.1~1.3 — 트리거, 문제 및 보고서 근거 확인
- [x] 2.1~2.5 — 기존 Epic 구조 유지 가능, 신규 Epic·재정렬 불필요
- [x] 3.1 — PRD 충돌 없음
- [x] 3.2 — 아키텍처 규칙과 정렬
- [x] 3.3 — UX 구조 변경 없음
- [x] 3.4 — 테스트 기준만 구체화
- [x] 4.1 — Direct Adjustment 실행 가능
- [N/A] 4.2 — 롤백 불필요
- [N/A] 4.3 — MVP 범위 재검토 불필요
- [x] 4.4 — Direct Adjustment 선택
- [x] 5.1~5.5 — 이슈, 영향, 접근, 실행 항목, 인계 정의
- [x] 6.1~6.2 — 제안 정확성과 범위 검토
- [x] 6.3 — 사용자 승인 완료
- [N/A] 6.4 — Sprint status 변경 불필요
- [x] 6.5 — `epics.md` 적용 및 검증 완료

## 6. 구현 인계

- 변경 등급: Minor
- 실행 담당: Developer
- 수정 대상: `epics.md`의 Story 1.4, 1.7, 2.1만
- 금지 범위: 전체 Epic 재생성, 다른 Story 수정, PRD·Architecture·UX 변경

### 성공 기준

- 세 Story에 제안된 인수 조건이 정확히 추가된다.
- 다른 Story와 Epic 구조는 변경되지 않는다.
- `git diff --check`가 통과한다.
- 변경 diff가 구현 준비성 보고서의 우선 권고 1~3과 일치한다.
