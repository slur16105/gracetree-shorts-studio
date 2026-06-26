# Story 2.14: macOS 설치 패키지

Status: done

## Story

As a macOS 사용자,
I want Apple Silicon 설치 패키지를 설치하고 싶다,
so that 포함된 엔진과 FFmpeg로 로컬 생성할 수 있다.

## Acceptance Criteria

1. macOS 환경에서 electron-builder로 엔진·FFmpeg·모델을 ASAR 밖에 포함한 arm64 설치본을 만들고 앱 시작과 포함 바이너리 실행 검사를 통과한다.

## Tasks / Subtasks

- [x] macOS arm64 engine·FFmpeg·model artifact와 executable permission을 검증한다. (AC: 1)
- [x] electron-builder mac target과 extraResources, hardened-runtime 준비 설정을 구성한다. (AC: 1)
- [x] installer artifact, checksums, licenses, build metadata를 생성한다. (AC: 1)
- [x] clean Apple Silicon 환경에서 설치·Gatekeeper 개발 흐름·앱 시작·migration·binary health를 검증한다. (AC: 1)
- [x] app bundle 이동 후 resource resolution과 Finder open 동작을 확인한다. (AC: 1)

## Dev Notes

- macOS arm64 빌드는 macOS arm64 환경에서 생성한다. Intel 지원은 MVP 범위가 아니다.
- 실제 서명·notarization pass/fail gate는 Story 2.17이 소유한다. 이 Story는 이후 서명이 가능한 구조를 깨지 않는다.
- 실행 권한과 quarantine 환경을 스모크 테스트에서 확인한다.

### Expected File Changes

- `apps/desktop/electron-builder.yml`
- `scripts/{build-desktop.mjs,verify-package.mjs}`
- `.github/workflows/release.yml`
- `tests/smoke/macos/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#story-214-macos-설치-패키지]
- [Source: _bmad-output/planning-artifacts/architecture.md#인프라-및-배포]
- https://www.electron.build/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/2-14-macos-설치-패키지.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/desktop/resources/entitlements.mac.plist`
- `tests/smoke/macos/README.md`
- `tests/smoke/macos/install.sh`
- `tests/smoke/macos/smoke-check.sh`
