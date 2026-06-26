# Story 2.16: 7일 안정성 검증 계획

## Release Candidate 식별

| 항목               | 값                                             |
|--------------------|------------------------------------------------|
| RC 빌드 커밋 SHA   | `<sha — 검증 시작 전 여기에 기록>`             |
| 인스톨러 파일명    | `<예: GraceTree-Shorts-Studio-0.1.0-windows-x64-setup.exe>` |
| 인스톨러 SHA-256   | `<체크섬 여기에 기록>`                         |
| 검증 시작일        | `<YYYY-MM-DD>`                                 |
| 예정 종료일        | `<시작일 + 7일>`                               |
| 검증 환경          | `<예: Windows 11 x64, Apple Silicon M2>`       |

> **주의**: RC 빌드를 교체하거나 설정을 변경하면 새 검증 주기로 재시작한다.

## 성공 기준

1. 7일 중 **매일 한 개 이상** publish-date 작업을 생성·렌더링한다.
2. 치명적 데이터 손상(SQLite CORRUPT, input hash 불일치)이 **0건**이다.
3. 실패 시 **복구 가능한 오류**로 종료하고 입력 파일과 기존 결과가 보존된다.
4. 시도(attempt) 로그가 매일 `day-logs/day-NN.md`에 기록된다.

## 실패 분류

| 분류          | 설명                                           | 처리                    |
|---------------|------------------------------------------------|-------------------------|
| RECOVERABLE   | 오류 메시지 + 이전 결과 보존                   | 기록 후 계속            |
| FATAL         | 데이터 손상 또는 앱 재시작 후에도 작업 불가    | 검증 즉시 중단, 이슈 제출 |
| SKIP          | 의도적으로 해당 날 건너뜀 (사유 기록 필수)    | 연속일 수 초기화         |

## 7일 일정

| 날짜       | Publish Date (예시) | 상태 | 기록 링크           |
|------------|---------------------|------|---------------------|
| Day 1      | 다음 주 월요일      | —    | `day-logs/day-01.md` |
| Day 2      | 다음 주 화요일      | —    | `day-logs/day-02.md` |
| Day 3      | 다음 주 수요일      | —    | `day-logs/day-03.md` |
| Day 4      | 다음 주 목요일      | —    | `day-logs/day-04.md` |
| Day 5      | 다음 주 금요일      | —    | `day-logs/day-05.md` |
| Day 6      | 다음 주 토요일      | —    | `day-logs/day-06.md` |
| Day 7      | 다음 주 일요일      | —    | `day-logs/day-07.md` |

## 샘플 콘텐츠 요구사항

- 입력 파일(영상/음성): `tests/fixtures/stability/` 에 커밋된 고정 샘플 사용
- 스크립트: 날짜별로 다른 타이틀을 사용해 중복 없이 생성한다
- BGM: 고정 테스트 BGM 파일 사용

## 일일 수행 절차

```
1. 앱 종료 후 재시작 (app restart 포함)
2. 새 publish date 선택 → 입력 파일 등록 → 스크립트 설정
3. 생성 실행 → 완료 대기
4. daily-check 스크립트 실행:
   - macOS: ./tests/stability/daily-check.sh
   - Windows: .\tests\stability\daily-check.ps1
5. day-logs/day-NN.md에 결과 기록
```
