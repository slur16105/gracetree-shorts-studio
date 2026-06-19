# Story 1.7: 공통 리소스 설정과 작업별 BGM 적용

Status: ready-for-dev

## Story

As a 개인 제작자,
I want 반복 사용하는 영상·음악·폰트를 설정하고 작업별 BGM을 선택적으로 적용하고 싶다,
so that 매 작업마다 공통 파일을 다시 등록하지 않고 일관된 결과를 만들 수 있다.

## Acceptance Criteria

1. 설정 모달에 제목·말씀 영상, 기도 반복 영상, 기본 BGM, 자막 폰트의 파일명과 유효 상태를 한 화면에 표시하고 모달을 중첩하지 않는다.
2. 필수 리소스 누락·읽기 실패를 준비 상태에 반영하고 `설정 열기`를 제공한다.
3. 새 리소스 복사·검증 성공 후 `resources` 폴더와 메타데이터를 갱신해 이후 작업부터 사용한다.
4. 교체 실패 시 행별 오류·해결 동작을 표시하고 기존 정상 리소스를 유지한다.
5. 작업별 BGM이 없으면 유효한 기본 BGM을 사용하고 그 상태를 홈에 표시한다.
6. 작업별 BGM은 해당 작업에서만 우선하며 기본 BGM 설정을 변경하지 않는다.
7. 공통 리소스 교체를 기존 완료 결과에 소급 적용하지 않는다.
8. 모달 포커스 제한·복원과 각 리소스·교체 버튼의 접근성 이름을 제공한다.
9. `resources` 순차 마이그레이션에 지정 열, 지원 종류 제약, `uq_resources_resource_type`, `idx_resources_status`를 추가하고 빈/직전 DB에서 데이터 보존을 검증한다.

## Tasks / Subtasks

- [ ] `003_create_resources.sql`과 resource repository를 구현한다. (AC: 3, 4, 9)
- [ ] 지원 resource type과 상태, resource DTO를 공유 계약으로 정의한다. (AC: 1~9)
- [ ] file dialog→임시 복사→유형/가독성 검증→원자적 교체 service를 구현한다. (AC: 3, 4, 7)
- [ ] 설정 dialog 내용을 Story 1.2 shell에 연결하고 행별 상태·교체·포커스 동작을 구현한다. (AC: 1~4, 8)
- [ ] readiness와 BGM resolver에 `job override > valid default > missing` 우선순위를 구현한다. (AC: 2, 5, 6)
- [ ] migration, 교체 rollback, 기존 완료 불변, modal accessibility 테스트를 추가한다. (AC: 1~9)

## Dev Notes

- 승인된 Sprint Change Proposal이 `resources` 테이블 최초 소유권을 이 Story에 부여한다.
- 파일 교체 확인용 중첩 모달을 만들지 않는다. 시스템 파일 선택 후 같은 설정 dialog 행에서 결과를 처리한다.
- 기존 정상 리소스는 새 사본 검증과 DB 갱신이 모두 성공하기 전까지 삭제·교체하지 않는다.
- 작업 시작 시점에 실제 사용 리소스를 스냅샷한다. 이후 설정 변경이 실행 중 작업이나 완료 결과에 영향을 주면 안 된다.

### Expected File Changes

- `engine/migrations/003_create_resources.sql`
- `engine/gracetree_engine/storage/resource_repository.py`
- `apps/desktop/src/main/{resources/resource-paths.ts,ipc/register-resource-handlers.ts}`
- `apps/desktop/src/renderer/src/features/resources/`
- `packages/contracts/src/desktop-api.ts`

### Testing Requirements

- resource type unique·status index·빈/002 DB migration과 기존 job/input 보존을 검증한다.
- 잘못된 영상/오디오/폰트, copy failure, DB failure에서 기존 리소스가 유지되는지 확인한다.
- BGM 우선순위, 설정 dialog focus trap/Esc/복원, 중첩 방지를 검증한다.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#story-17-공통-리소스-설정과-작업별-bgm-적용]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-19.md#story-17--acceptance-criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md#사용자-데이터-디렉터리]
- https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/1-7-공통-리소스-설정과-작업별-bgm-적용.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
