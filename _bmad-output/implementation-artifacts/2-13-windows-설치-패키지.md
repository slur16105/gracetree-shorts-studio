# Story 2.13: Windows 설치 패키지

Status: ready-for-dev

## Story

As a Windows 사용자,
I want x64 설치 패키지를 설치하고 싶다,
so that 포함된 엔진과 FFmpeg로 로컬 생성할 수 있다.

## Acceptance Criteria

1. Windows 환경에서 electron-builder로 엔진·FFmpeg·모델을 ASAR 밖에 포함한 x64 설치본을 만들고 앱 시작과 포함 바이너리 실행 검사를 통과한다.

## Tasks / Subtasks

- [ ] Windows x64 engine·FFmpeg·model artifact의 검증된 입력 경로를 준비한다. (AC: 1)
- [ ] `electron-builder.yml`의 extraResources/asarUnpack와 runtime resolver를 구성한다. (AC: 1)
- [ ] installer artifact, checksums, licenses, build metadata를 생성한다. (AC: 1)
- [ ] clean Windows VM에서 설치·앱 시작·migration·engine health·FFmpeg probe를 검증한다. (AC: 1)
- [ ] packaged path에 공백·비ASCII가 있어도 args array 실행이 동작하는지 확인한다. (AC: 1)

## Dev Notes

- Windows 빌드는 Windows runner에서 수행한다. macOS/Linux에서 생성한 native 자산을 재사용하지 않는다.
- 서명은 Story 2.17 gate 소유다. 개인 개발 installer는 unsigned 가능하되 외부 배포본으로 표시하지 않는다.
- 사용자에게 Python·FFmpeg PATH 설정을 요구하면 실패다.

### Expected File Changes

- `apps/desktop/electron-builder.yml`
- `scripts/{build-desktop.mjs,verify-package.mjs}`
- `.github/workflows/release.yml`
- `tests/smoke/windows/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#story-213-windows-설치-패키지]
- [Source: _bmad-output/planning-artifacts/architecture.md#인프라-및-배포]
- https://www.electron.build/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/2-13-windows-설치-패키지.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
