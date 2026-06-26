# GraceTree Shorts Studio

교회 단편 영상(Shorts)을 로컬에서 자동 제작하는 데스크톱 앱이다.  
음성 파일과 스크립트를 준비하면 자막·배경·BGM이 합성된 완성 영상을 만들어준다.  
인터넷 연결 없이 완전히 오프라인으로 동작한다.

---

## 목차

1. [필수 환경](#필수-환경)
2. [개발 환경 설정](#개발-환경-설정)
3. [앱 실행](#앱-실행)
4. [테스트](#테스트)
5. [빌드 및 패키징](#빌드-및-패키징)
6. [앱 사용 방법](#앱-사용-방법)
7. [프로젝트 구조](#프로젝트-구조)
8. [AI 에이전트 / BMAD 워크플로](#ai-에이전트--bmad-워크플로)

---

## 필수 환경

| 도구 | 버전 | 용도 |
|------|------|------|
| Node.js | 26.x | Electron / TypeScript 빌드 |
| pnpm | 11.8.0 | JS 패키지 관리 |
| Python | 3.11 – 3.13 | 엔진 (음성 정렬, ffmpeg 파이프라인) |
| ffmpeg / ffprobe | 최신 안정 버전 | 영상·오디오 처리 |

**ffmpeg 설치:**

```bash
# macOS
brew install ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg
```

---

## 개발 환경 설정

```bash
# 1. 저장소 클론
git clone <repo-url>
cd gracetree-shorts-studio

# 2. JS 의존성 설치
pnpm install --frozen-lockfile

# 3. Python 의존성 설치
cd engine
pip install -e ".[dev]"
cd ..
```

---

## 앱 실행

```bash
# 개발 모드 (핫 리로드)
pnpm dev
```

Electron 창이 열리고 React 렌더러가 실시간으로 갱신된다.  
Python 엔진은 영상 생성 요청 시 자동으로 서브프로세스로 실행된다.

---

## 테스트

```bash
# 전체 테스트 (TypeScript + Python + 통합)
pnpm test

# TypeScript 단위 테스트만
pnpm test:ts

# Python 단위 테스트만
pnpm test:python

# E2E 테스트 (Playwright)
pnpm test:e2e

# 통합 테스트 (엔진 헬스 체크)
pnpm test:integration
```

**Python 테스트를 직접 실행할 때:**

```bash
cd engine
python -m pytest
```

> Python 테스트는 반드시 `engine/` 디렉터리 안에서 실행해야 한다.  
> 루트에서 실행하면 `ModuleNotFoundError`가 발생한다.

**전체 CI 검증:**

```bash
pnpm ci   # verify-python-lock + typecheck + lint + test
```

---

## 빌드 및 패키징

### Electron 앱만 빌드

```bash
pnpm --filter gracetree-desktop build
```

### 설치 패키지 생성

```bash
# macOS (Apple Silicon)
node scripts/build-desktop.mjs --platform darwin --arch arm64

# Windows x64
node scripts/build-desktop.mjs --platform win32 --arch x64
```

빌드 결과물은 `apps/desktop/dist/` 아래에 생성된다.

### 스모크 테스트 (macOS)

```bash
# DMG 설치 후 기본 동작 검증
tests/smoke/macos/install.sh /path/to/GraceTree-Shorts-Studio-*-macos-arm64.dmg
tests/smoke/macos/smoke-check.sh
```

### 서명 검증

```bash
node scripts/verify-signing.mjs
```

---

## 앱 사용 방법

앱을 실행하면 화면 오른쪽 상단의 **가이드** 버튼으로 인앱 가이드를 열 수 있다.  
가이드에는 다음 내용이 포함되어 있다.

| 섹션 | 내용 |
|------|------|
| 첫 영상 만들기 | 날짜 선택 → 파일 등록 → 생성의 3단계 흐름 |
| 파일명 규칙 | `voice.*`, `bgm.*` 자동 분류 규칙 |
| 스크립트 작성법 | `[제목]`, `[말씀]`, `[기도]` 필수 구역 형식 |
| 오류 해결 | 파일 등록·생성 중 자주 발생하는 오류와 조치 |
| 저장 위치 | `input/`, `output/`, `logs/` 폴더 구조 설명 |
| 앱 정보 | 버전, 오프라인 동작 원칙 |

### 빠른 시작 요약

1. **게시 날짜 선택** — 홈 화면에서 달력 버튼을 눌러 날짜를 고른다.
2. **파일 등록** — 음성(`voice.mp3`), 배경음악(`bgm.mp3`), 스크립트(`.txt`), 썸네일 파일을 드래그하거나 버튼으로 선택한다.
3. **스크립트 형식** — 아래 구조로 작성한다.
   ```
   [제목]
   오늘의 은혜

   [말씀]
   성경 본문 내용

   [기도]
   기도 내용
   ```
4. **영상 생성** — 모든 슬롯이 정상 상태가 되면 생성 버튼을 누른다.
5. **결과 확인** — 완료 후 게시 날짜 폴더의 `output/` 디렉터리에서 완성 영상을 확인한다.

---

## 프로젝트 구조

```
gracetree-shorts-studio/
├── apps/
│   └── desktop/                  # Electron 앱
│       └── src/
│           ├── main/             # Electron main process (IPC, EngineClient)
│           ├── preload/          # contextBridge
│           └── renderer/src/     # React UI
│               └── features/     # guide, job-editor, history 등
├── engine/                       # Python 엔진 패키지
│   └── gracetree_engine/
│       ├── jobs/                 # orchestrator, job 관리
│       ├── media/                # runner, compose, background
│       ├── speech/               # aligner, config, benchmark
│       ├── storage/              # SQLite repositories, migrations
│       ├── diagnostics/          # logger, verifier
│       └── subtitles/            # ASS 자막 생성
├── packages/
│   └── contracts/                # 공유 JSON Schema + TypeScript 타입
├── tests/
│   ├── integration/              # 엔진 통합 테스트
│   ├── quality/                  # 수동 품질 평가 양식
│   └── smoke/                    # macOS / Windows 스모크 테스트
├── scripts/                      # 빌드·검증 스크립트
├── _bmad-output/                 # BMAD 산출물 (기획·구현 아티팩트)
├── AGENTS.md                     # 코딩 에이전트 공통 계약
└── _bmad-output/project-context.md  # AI 에이전트 구현 규칙 요약
```

### 핵심 통신 구조

```
Electron Renderer (React)
        ↕ contextBridge
Electron Main (IPC)
        ↕ JSON Lines (stdin/stdout)
Python Engine (gracetree_engine)
        ↕ subprocess
ffmpeg / ffprobe
```

---

## AI 에이전트 / BMAD 워크플로

이 프로젝트는 [BMAD(Behavior-Metrics-Acceptance-Design)](https://github.com/bmad-dev) 워크플로로 개발한다.  
Claude Code + BMAD 스킬을 조합해 Story 단위로 TDD 구현을 진행한다.

### 에이전트 세션 시작 전 필독 파일

| 파일 | 목적 |
|------|------|
| `AGENTS.md` | 에이전트 공통 행동 계약 (우선순위, 금지 항목) |
| `_bmad-output/project-context.md` | 구현 규칙 30개 요약 (비자명한 패턴 중심) |
| `_bmad-output/planning-artifacts/architecture.md` | 기술 결정과 구조 |

### 주요 스킬

```bash
/bmad-create-story   # 다음 Story 파일 생성
/bmad-dev-story      # Story 구현 (TDD red→green→refactor)
/code-review         # 코드 리뷰 실행
/bmad-help           # 현재 위치와 다음 단계 안내
```

### 스프린트 상태 확인

```bash
cat _bmad-output/implementation-artifacts/sprint-status.yaml
```

### 개발 루프

```
create-story → dev-story (TDD) → code-review → 수정 반영 → commit → next story
```
