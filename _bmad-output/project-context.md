---
project_name: 'gracetree-shorts-studio'
user_name: 'Slur'
date: '2026-06-27'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 30
optimized_for_llm: true
---

# Project Context for AI Agents

이 파일은 이 프로젝트에서 코드를 구현할 때 AI 에이전트가 반드시 따라야 하는 규칙과 패턴을 담고 있다.
명백한 내용은 생략하고, LLM이 놓치기 쉬운 비자명한 세부사항에 집중한다.

---

## 기술 스택 & 버전

### Desktop (Electron + React)
- Electron ^39.2.6, electron-vite ^5.0.0
- React ^19.2.1, React DOM ^19.2.1
- TypeScript ^5.9.3
- Vite ^7.2.6
- vitest 4.0.16 (단위/컴포넌트 테스트)
- @playwright/test 1.61.0 (E2E)
- @testing-library/react ^16.3.2
- CSS Modules (`.module.css`)

### Python 엔진
- Python 3.11–3.14
- faster-whisper ≥1.0.0 (음성 인식)
- jsonschema 4.25.1 (JSON 스키마 검증)
- SQLite3 (stdlib, DB)
- pytest (테스트)
- setuptools 80.9.0 (빌드)

### 공유 계약
- `packages/contracts/` — JSON Schema + TypeScript 타입
- AJV 2020 (TS 측 스키마 검증)
- Electron ↔ Python 통신: JSON Lines over stdin/stdout

---

## Critical Implementation Rules

### Python 엔진

- **`from __future__ import annotations`** — 모든 Python 파일 첫 줄에 필수. 누락 시 타입 힌트 평가 오류 발생.
- **`tests/`에 `__init__.py` 없음** — helpers 임포트 시 `sys.path.insert(0, os.path.dirname(__file__))` 사용 후 `from helpers import ...` 방식만 허용. `from .helpers import ...` (상대 임포트) 사용 금지.
- **subprocess는 반드시 `run_safe()` 사용** — `engine/gracetree_engine/media/runner.py`의 `run_safe()`만 허용. `shell=True` 절대 금지. ffmpeg/ffprobe 외 실행파일 추가 시 `ALLOWED_EXECUTABLES`에 먼저 등록.
- **관리 경로 경계 검사** — 사용자 제공 경로는 반드시 `_assert_within_root(path, approved_root)` 검사 후 사용. 미검사 경로로 파일 쓰기/복사 금지.
- **에러 메시지 경로 redact** — `VerificationError`·`AlignmentError` 등 외부 노출 메시지에 파일 경로가 포함될 경우 반드시 `redact_paths()` 적용.
- **`_assert_within_root` 패턴** — 경계 위반은 `ValueError`로 발생, 호출부에서 catch 후 `job_failed` 이벤트 emit.
- **`AlignmentError` / `VerificationError` 구조** — `error_code: str`, `message: str` 생성자 형식. `error_code`는 영문 대문자 스네이크.
- **DB atomic 쓰기** — JSON 파일 쓰기는 `.tmp` 임시 파일 → `rename/replace` 패턴 필수. 직접 쓰기 금지.
- **`completed_at` 보호** — 이미 완료된 작업의 `completed_at` 컬럼은 UPDATE로 덮어쓰지 않는다.
- **cancel race condition** — orchestrator에서 취소 이벤트 확인은 `_check_cancel(cancel_event)` 헬퍼 사용, 각 stage 시작 전 호출.
- **16kHz WAV 포맷** — 음성 파일 테스트용 임시 WAV 생성 시 `tests/helpers.py`의 `make_silent_wav()` 재사용. 직접 struct 작성 금지.
- **stderr 길이 제한** — 에러 메시지에 stderr 포함 시 `STDERR_MAX_CHARS` (500) 상수 사용. 매직 넘버 하드코딩 금지.

### TypeScript / Electron

- **IPC 채널 상수** — `packages/contracts/src/desktop-api.ts`의 `*_CHANNEL` 상수 사용. 채널 이름 문자열 하드코딩 금지.
- **전역 UI 상태** — `useSyncExternalStore` 패턴 사용 (예: `job-progress-store.ts`). Redux/Zustand 등 외부 상태 라이브러리 도입 금지.
- **계약 타입 임포트** — `@gracetree/contracts` workspace 패키지에서 임포트. 로컬 타입 재정의 금지.
- **네비게이션 정책** — `navigation-policy.ts`의 `shouldBlockNavigation()` 로직을 우회하는 새 `webContents` 이벤트 핸들러 등록 금지.
- **CSS Modules** — 스타일은 `.module.css`로만 작성. 인라인 스타일 및 global CSS 직접 작성 금지 (기존 `styles/` 내 전역 변수 제외).

### 통신 프로토콜 (Electron ↔ Python)

- **JSON Lines** — 엔진 명령/이벤트는 반드시 단일 JSON 객체를 한 줄로 stdout에 출력 후 `\n`. 멀티라인 JSON 금지.
- **protocolVersion: 1** — 모든 명령/이벤트에 `"protocolVersion": 1` 필드 필수.
- **스키마 검증** — Python 측 이벤트 emit 전, TypeScript 측 명령 수신 후 각각 JSON Schema로 검증.
- **jobId 일관성** — 명령과 응답 이벤트의 `jobId`는 동일해야 함.

### 테스트

- **TDD 순서** — red(실패 테스트 작성) → green(최소 구현) → refactor. 구현 먼저 작성 후 테스트 추가 금지.
- **Python mock 대상** — subprocess 모킹 시 `gracetree_engine.media.runner.subprocess.run` 또는 `gracetree_engine.diagnostics.verifier.run_safe` 등 **실제 사용 모듈 내 이름** 기준으로 patch. `subprocess.run` 전역 패치 금지.
- **더미 WAV** — `tests/helpers.py`의 `make_silent_wav(path)` 활용. 직접 바이트 조립 금지.
- **pytest 통합 테스트 skip** — ffmpeg 미설치 환경에서 실제 ffmpeg 호출 테스트는 `@pytest.mark.integration` 마킹 후 조건부 skip.
- **vitest 파일 컨벤션** — `*.test.ts` / `*.test.tsx` 패턴. 테스트는 대상 파일과 동일 디렉터리에 위치.

### 보안 / 안전

- **`shell=True` 절대 금지** — subprocess, `os.system()`, eval 등 모든 셸 실행 경로 금지.
- **경로 traversal** — 사용자 입력 경로는 반드시 `_assert_within_root()` 통과 후 사용.
- **ffmpeg/ffprobe allowlist** — `runner.py`의 `ALLOWED_EXECUTABLES`에 없는 바이너리 실행 금지.
- **네비게이션 차단** — Electron webContents에서 외부 URL로의 navigate/redirect 금지. `shouldBlockNavigation()` 유지.

---

## 프로젝트 구조 핵심

```
gracetree-shorts-studio/
├── apps/desktop/          # Electron 앱
│   └── src/
│       ├── main/          # Electron main process (IPC handlers, EngineClient)
│       ├── preload/       # contextBridge
│       └── renderer/src/  # React UI (features/, components/, hooks/)
├── engine/                # Python 엔진 패키지
│   └── gracetree_engine/
│       ├── jobs/          # orchestrator, job 관리
│       ├── media/         # runner, compose, background
│       ├── speech/        # aligner, config, benchmark
│       ├── storage/       # SQLite repositories, migrations
│       ├── diagnostics/   # logger, verifier
│       └── subtitles/     # ASS 자막 생성
└── packages/contracts/    # 공유 스키마 & TypeScript 타입
```

---

## Usage Guidelines

**For AI Agents:**

- 코드 구현 전에 이 파일을 반드시 먼저 읽는다.
- 모든 규칙을 정확하게 따른다.
- 불확실한 경우, 더 제한적인 옵션을 선택한다.
- 새로운 패턴이 등장하면 이 파일을 업데이트한다.

**For Humans:**

- 이 파일은 AI 에이전트의 필요에 집중해 간결하게 유지한다.
- 기술 스택이 변경될 때 업데이트한다.
- 분기별로 오래된 규칙을 검토하고 제거한다.
- 시간이 지나며 자명해진 규칙은 삭제한다.

Last Updated: 2026-06-27
