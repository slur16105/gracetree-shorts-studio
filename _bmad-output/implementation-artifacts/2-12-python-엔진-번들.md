# Story 2.12: Python 엔진 번들

Status: ready-for-dev

## Story

As a 개인 제작자,
I want Python을 별도 설치하지 않고 엔진을 실행하고 싶다,
so that 실제 제작 PC에서 설치 부담 없이 사용할 수 있다.

## Acceptance Criteria

1. PyInstaller onedir로 Python 미설치 환경에서 실행 가능한 엔진과 로컬 음성 자원을 만들고 버전·checksum·license 메타데이터를 기록한다.

## Tasks / Subtasks

- [ ] production entrypoint·hidden imports·native libraries·model data를 PyInstaller spec에 명시한다. (AC: 1)
- [ ] 플랫폼별 onedir build script와 deterministic metadata manifest를 구현한다. (AC: 1)
- [ ] 개발 module path와 packaged executable path를 resource resolver 뒤에 격리한다. (AC: 1)
- [ ] clean Python-missing 환경에서 health와 최소 수직 슬라이스를 실행한다. (AC: 1)
- [ ] 포함 파일의 version/checksum/license와 누락·변조 실패 테스트를 추가한다. (AC: 1)

## Dev Notes

- PyInstaller는 교차 컴파일하지 않는다. 각 OS에서 해당 번들을 만든다.
- onefile로 바꾸지 않는다. Architecture는 6.21 계열 onedir를 승인했다.
- 모델·native library가 런타임 다운로드를 시도하지 않도록 오프라인 실행을 검증한다.

### Expected File Changes

- `engine/packaging/gracetree-engine.spec`
- `scripts/build-engine.mjs`
- engine resource resolver와 package verification tests
- `resources/licenses/`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#story-212-python-엔진-번들]
- [Source: _bmad-output/planning-artifacts/architecture.md#인프라-및-배포]
- https://pyinstaller.org/en/stable/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

- `_bmad-output/implementation-artifacts/2-12-python-엔진-번들.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
