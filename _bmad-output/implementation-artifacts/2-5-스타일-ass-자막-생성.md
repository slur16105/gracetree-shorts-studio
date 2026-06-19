# Story 2.5: 스타일 ASS 자막 생성

Status: ready-for-dev

## Story

As a 개인 제작자,
I want 분석된 타이밍으로 한글 ASS 자막을 만들고 싶다,
so that 기존 영상 양식에 맞는 읽기 좋은 자막을 얻을 수 있다.

## Acceptance Criteria

1. 제목·말씀은 상단, 기도는 중앙에 배치하고 지정 폰트·색상·테두리·그림자·페이드를 적용하며 마지막 “아멘”은 약 2초 유지 후 약 0.5초 페이드아웃한다.
2. 안전 영역 이탈이나 한글 글리프 누락은 성공 처리하지 않고 원인을 기록하며 성공 시 UTF-8 `subtitles.ass`를 temp에 저장한다.

## Tasks / Subtasks

- [ ] timing DTO를 ASS event와 style로 변환하는 순수 generator를 구현한다. (AC: 1)
- [ ] 1080×1920 좌표계, 상단/중앙 safe area, 폰트·outline·shadow·fade 설정을 typed config로 둔다. (AC: 1, 2)
- [ ] ASS 특수문자·개행을 escape하고 UTF-8 출력을 보장한다. (AC: 1, 2)
- [ ] 폰트 파일의 한글 glyph 가용성과 event bounds를 렌더 전 검증한다. (AC: 2)
- [ ] golden ASS, 아멘 duration/fade, glyph·safe-area 실패 테스트를 추가한다. (AC: 1, 2)

## Dev Notes

- 자막 검증 없이 파일 존재만으로 성공 처리하지 않는다. 가능하면 FFmpeg/libass 렌더 검증과 프레임 샘플 검사를 결합한다.
- 사용자 스크립트 전문은 로그에 기록하지 않는다. block index·오류 범주만 남긴다.
- 설정 리소스의 폰트를 사용하며 시스템 폰트 우연성에 의존하지 않는다.

### Expected File Changes

- `engine/gracetree_engine/subtitles/`
- `engine/gracetree_engine/jobs/`
- `engine/tests/subtitles/`, golden fixtures

### References

- [Source: _bmad-output/planning-artifacts/epics.md#story-25-스타일-ass-자막-생성]
- [Source: _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/prd.md#fr-13-스타일-자막-생성]
- https://ffmpeg.org/ffmpeg-filters.html

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/2-5-스타일-ass-자막-생성.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
