---
baseline_commit: b1a6475
---

# Story 2.8: FFmpeg 파이프라인 통합 검증

Status: done

## Story

As a 개발 담당자,
I want 전체 미디어 파이프라인을 작은 샘플로 검증하고 싶다,
so that 단계별 기능이 결합될 때 발생하는 결함을 조기에 찾을 수 있다.

## Acceptance Criteria

1. 라이선스 안전 샘플로 파싱부터 임시 MP4까지 통합 실행하고 해상도, 프레임률, 오디오·영상 stream, 검은 프레임과 정지 구간을 자동 검사하며 단계별 시간과 민감정보 제거 진단을 기록한다.

## Tasks / Subtasks

- [x] 작고 결정적인 script/voice/image/BGM/video/font fixture 세트를 고정한다. (AC: 1)
- [x] 2.2~2.7 단계를 production orchestrator 경로로 실행하는 integration harness를 만든다. (AC: 1)
- [x] ffprobe로 dimensions/fps/duration/streams를 검사하고 blackdetect/freezedetect 기준을 적용한다. (AC: 1)
- [x] 단계별 wall time과 redacted command diagnostics를 attempt log에 기록한다. (AC: 1)
- [x] 실패 단계가 terminal failed로 귀결되고 partial output이 final로 이동하지 않는지 검증한다. (AC: 1)

## Dev Notes

- fixture는 라이선스와 생성 출처를 manifest로 기록한다. 실제 사용자 미디어를 커밋하지 않는다.
- codec·플랫폼 차이로 byte-for-byte MP4 비교를 요구하지 말고 stream·timing·frame 특성으로 검증한다.
- command log에서 사용자 절대 경로·스크립트 내용·미디어 내용은 제거한다.

### Expected File Changes

- `tests/integration/media-pipeline/`
- `tests/fixtures/media/` 및 license manifest
- `engine/gracetree_engine/diagnostics/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#story-28-ffmpeg-파이프라인-통합-검증]
- [Source: _bmad-output/planning-artifacts/architecture.md#테스트-로깅-및-품질-게이트]
- https://ffmpeg.org/ffprobe.html
- https://ffmpeg.org/ffmpeg-filters.html

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `engine/gracetree_engine/diagnostics/__init__.py`
- `engine/gracetree_engine/diagnostics/logger.py`
- `engine/gracetree_engine/diagnostics/verifier.py`
- `engine/tests/fixtures/integration/fixture-manifest.json`
- `engine/tests/integration/__init__.py`
- `engine/tests/integration/test_media_pipeline.py`
- `engine/tests/test_pipeline_diagnostics.py`
- `_bmad-output/implementation-artifacts/2-8-ffmpeg-파이프라인-통합-검증.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
