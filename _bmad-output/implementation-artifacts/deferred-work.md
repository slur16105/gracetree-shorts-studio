# Deferred Work

## Deferred from: code review of 1-3-게시-날짜별-작업-생성과-복원 (2026-06-20)

- 입력 메타데이터 schema/storage와 실제 복원은 `job_inputs` 및 파일 등록을 소유하는 Story 1.4에서 구현한다. Story 1.3은 빈 metadata 투영만 유지한다.

## Deferred from: code review of 1-5-입력-파일-자동-분류와-슬롯-관리 (2026-06-25)

- `assign_role` autocommit 추측 — `connect_database`가 autocommit 모드인지 diff만으로 검증 불가. 추후 DB 연결 레이어 감사 시 확인.
- FileSlot `replacement` stale 상태 — 현재 버그 없으나 `runAction` 분기 추가 시 stale replacement가 의도치 않게 실행될 위험. 향후 리팩터 시 `replacement`를 에러 후 즉시 초기화.
- 스키마 `conflict` 이름 중의성 — `results[*].status = "conflict"`(NAME_CONFLICT)와 `inputs[*].status = "conflict"`(역할 충돌)가 같은 이름이지만 다른 의미. 차후 스키마 버전 업 시 `name_conflict`로 구분.
- `invalid` 상태 E2E 테스트 없음 — 파일 읽기 불가 시나리오에 대한 전용 테스트가 없음. AC7 커버리지 개선 시 추가.
- `os.link` exFAT·외장드라이브 크래시 — 외장드라이브 미지원으로 defer 결정. managed root는 내부 드라이브만 지원.
