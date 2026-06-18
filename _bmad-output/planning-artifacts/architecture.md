---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/prd.md
  - _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/addendum.md
  - _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/polish-prose.md
  - _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/polish-structure.md
  - _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/reconcile-idea.md
  - _bmad-output/planning-artifacts/prds/prd-gracetree-shorts-studio-2026-06-19/review-rubric.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/EXPERIENCE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/polish-prose.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/polish-structure.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/reconcile-youtube-music-reference.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/review-accessibility.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/review-rubric.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/validation-report.md
  - _bmad-output/planning-artifacts/ux-designs/ux-gracetree-shorts-studio-2026-06-19/mockups/studio-black-reference.html
  - docs/idea.md
workflowType: architecture
lastStep: 8
status: complete
completedAt: 2026-06-19
project_name: gracetree-shorts-studio
user_name: Slur
date: 2026-06-19
---

# 아키텍처 결정 문서

_이 문서는 단계별 공동 탐색을 통해 구축되며, 합의된 아키텍처 결정을 순차적으로 추가한다._

## 프로젝트 컨텍스트 분석

### 요구사항 개요

**기능 요구사항:**

24개 기능 요구사항은 다음 5개 영역으로 구성된다.

- 날짜별 입력 등록·분류·검증 및 공통 리소스 관리
- 스크립트·음성 분석과 자막·영상·오디오 합성
- 생성 단계, 진행률, 취소 및 중복 실행 방지
- 성공·실패 안내와 안전한 재생성
- 최근 작업, 완료 목록 및 결과 폴더 연결

아키텍처의 핵심은 UI와 장시간 실행되는 생성 파이프라인을 분리하면서도 파일 상태와 작업 상태를 일관되게 유지하는 것이다.

**비기능 요구사항:**

- Windows와 macOS에서 동작하는 로컬 설치형 애플리케이션
- 네트워크 없이 정상 작동하며 입력·결과를 외부로 전송하지 않음
- UI 상태를 생성 단계 변경 후 1초 이내 갱신
- 실패·취소·비정상 종료가 기존 완료 결과를 손상시키지 않아야 함
- 재생성 성공 전까지 기존 결과 유지
- 원본 파일 불변, 등록 파일 복사, 임시 파일 정리
- 기술 로그와 사용자용 오류 메시지 분리
- WCAG 2.2 AA, 키보드 조작, 200% 확대 지원
- 핵심 생성 기능을 UI 및 저장 방식과 분리

**규모와 복잡도:**

- 주요 도메인: 로컬 데스크톱 UI와 미디어 처리 파이프라인
- 복잡도: 중간 이상
- 예상 아키텍처 구성요소: 약 8개
- 실시간 협업·다중 사용자·규제 준수: 없음
- 외부 통합: 최소
- 미디어 처리 및 로컬 파일 안전성: 높음
- 사용자 상호작용 복잡도: 중간
- 데이터 규모: 작업 수는 작지만 영상 파일은 큼

### 기술적 제약 및 의존성

- FFmpeg 기반 영상·오디오 합성이 필요하다.
- 로컬 음성 분석 엔진이 필요하며 외부 음성 API는 기본 경로에서 제외된다.
- 대용량 미디어를 UI 프로세스 메모리에 적재하지 않아야 한다.
- 장시간 프로세스의 진행 이벤트, 취소 및 강제 종료를 제어해야 한다.
- 운영체제 파일 선택기와 Explorer/Finder 연동이 필요하다.
- 게시 날짜는 사용자 식별 기준이지만 내부 작업 식별자와 분리할 필요가 있다.
- 작업 폴더, 임시 출력, 완료 출력 사이의 명확한 수명주기가 필요하다.
- 기준 PC 사양과 렌더링 성능 예산은 아직 미확정이다.
- 구체적인 데스크톱 패키징 방식과 UI 기술은 아직 결정되지 않았다.

### 확인된 횡단 관심사

- 작업 상태 머신과 애플리케이션 재시작 후 복구
- 파일 복사·교체·재생성의 원자성과 멱등성
- 취소 가능한 하위 프로세스 관리
- 진행률 이벤트의 표준 형식
- 사용자 오류와 기술 오류의 분류
- 작업별 진단 로그와 산출물 추적
- 경로 처리와 Windows/macOS 차이 격리
- 공통 리소스 버전과 작업별 입력 스냅샷
- UI·작업 관리·생성 엔진 사이의 계약
- 영상 생성 규칙의 재현성과 테스트 가능성
- 접근성과 키보드 포커스 관리
- 기존 완료 결과를 보호하는 안전한 커밋 절차

이 프로젝트는 단순한 데스크톱 UI가 아니라 로컬 트랜잭션 안전성을 갖춘 미디어 작업 실행기로 다룬다.

## 스타터 템플릿 평가

### 주요 기술 도메인

로컬 미디어 처리 엔진을 포함한 크로스 플랫폼 데스크톱 애플리케이션이다.

### 검토한 스타터 옵션

**Tauri 2.11.2**

- React와 TypeScript 프런트엔드 템플릿을 제공한다.
- 설치 결과와 메모리 사용량을 줄이는 데 유리하다.
- Python·FFmpeg 등 외부 바이너리는 운영체제와 CPU 아키텍처별 sidecar로 구성해야 한다.
- Rust 명령 계층과 Tauri 권한 설정이 추가되므로 현재 MVP의 프로세스·패키징 복잡도가 증가한다.

**Electron Forge**

- Electron 공식 패키징·배포 도구이며 TypeScript 스타터를 제공한다.
- 공식 Vite 플러그인은 현재 문서에서 experimental로 표시되어 있다.
- Electron 앱 수명주기와 배포 도구를 한 체계에서 관리할 수 있으나 React 통합을 추가 구성해야 한다.

**electron-vite 5.0.0**

- React/TypeScript 템플릿을 제공한다.
- Electron의 main, preload, renderer 빌드를 하나의 설정에서 관리한다.
- renderer HMR과 main/preload hot reload를 지원한다.
- electron-builder 또는 Electron Forge와 결합해 Windows/macOS 배포물을 만들 수 있다.

### 선택한 스타터: Electron + electron-vite + React/TypeScript

**선택 근거:**

- Python·FFmpeg 프로세스 실행, 표준 입출력 이벤트 수신과 취소 제어가 직접적이다.
- Windows와 macOS에서 동일한 Chromium 기반 UI 렌더링 결과를 제공한다.
- Electron의 main/preload/renderer 구조가 UI와 운영체제 권한을 분리한다.
- 서버 렌더링이나 API 라우트가 필요하지 않으므로 Next.js보다 React + Vite가 단순하다.
- Python·FFmpeg 등 실행 바이너리를 ASAR 외부 리소스로 패키징할 수 있다.
- Electron의 설치 용량과 메모리 비용보다 MVP의 구현·배포 안정성이 우선한다.

**초기화 명령:**

```bash
npm create @quick-start/electron@latest apps/desktop -- --template react-ts
```

**스타터가 제공하는 아키텍처 결정:**

**언어 및 런타임:**

- renderer, preload, main 프로세스에 TypeScript를 사용한다.
- UI에는 React를 사용한다.
- 데스크톱 런타임에는 Electron을 사용한다.
- 구현 시 검증된 Electron 안정 버전을 고정하고 의도적으로 업그레이드한다.

**스타일링:**

- 스타터는 특정 디자인 시스템을 강제하지 않는다.
- UX 문서의 디자인 토큰을 구현할 CSS 체계는 후속 결정에서 확정한다.

**빌드 도구:**

- electron-vite와 Vite가 main, preload, renderer를 각각 빌드한다.
- 배포물 생성에는 electron-builder를 추가한다.
- Python·FFmpeg·음성 분석 바이너리는 ASAR에 포함하지 않고 애플리케이션 리소스로 배치한다.

**테스트 프레임워크:**

- 스타터가 테스트 프레임워크를 결정하지 않는다.
- UI 단위 테스트, 프로세스 계약 테스트와 생성 엔진 테스트는 후속 결정에서 확정한다.

**코드 구성:**

- `apps/desktop`에 Electron UI와 운영체제 어댑터를 둔다.
- Python 생성 엔진은 별도 패키지 경계로 둔다.
- renderer는 직접 파일 시스템이나 프로세스 API를 호출하지 않고 preload가 노출한 제한된 계약만 사용한다.

**개발 경험:**

- renderer HMR을 지원한다.
- main/preload 변경 시 Electron 프로세스를 다시 로드한다.
- TypeScript 타입 검사와 Electron 프로세스별 빌드를 제공한다.

**참고:** 이 초기화 명령 실행은 첫 번째 구현 스토리에서 수행한다.

## 핵심 아키텍처 결정

### 데이터 아키텍처

**결정: SQLite를 작업 상태와 완료 이력의 유일한 메타데이터 저장소로 사용한다.**

- SQLite에는 내부 작업 ID, 게시 날짜, 제목, 작업 상태, 입력 경로, 결과 경로, 실제 생성일, 실패 단계와 오류 범주를 저장한다.
- 입력 미디어와 생성 산출물은 게시 날짜별 애플리케이션 관리 폴더에 저장한다.
- 별도 작업별 `manifest.json`은 MVP에 포함하지 않는다.
- 앱 시작 시 SQLite 기록과 실제 입력·결과 파일의 존재 여부를 대조해 누락 상태와 중단된 작업을 식별한다.
- 게시 날짜 중복 방지는 데이터베이스 제약과 애플리케이션 검증을 함께 사용한다.
- 재생성은 새 결과를 임시 위치에 생성한 뒤 성공한 경우에만 기존 결과와 데이터베이스 기록을 교체한다.
- 스키마 변경은 순차 번호가 있는 명시적 마이그레이션으로 관리한다.
- SQLite 라이브러리는 별도 네이티브 Node 모듈을 추가하지 않고 패키징된 Python 런타임의 표준 `sqlite3` 모듈을 사용한다.

**선택 근거:**

- 완료 목록, 게시 날짜 중복 검사와 상태 조회를 파일 순회보다 안정적으로 처리한다.
- SQLite 트랜잭션을 사용해 재생성과 상태 전이를 원자적으로 기록할 수 있다.
- 작업별 manifest를 함께 운용할 때 발생하는 이중 기록과 불일치 문제를 MVP에서 피한다.

**영향 범위:** 작업 저장소, 완료 목록, 날짜 검증, 재생성, 앱 시작 복구, 스키마 마이그레이션.

### 인증 및 보안

**결정: 인증 기능 없이 최소 권한의 로컬 프로세스 경계를 적용한다.**

- 단일 사용자 로컬 MVP이므로 로그인, 사용자 계정과 권한 역할은 구현하지 않는다.
- Electron renderer에서는 Node.js 직접 접근을 금지한다.
- `contextIsolation: true`와 renderer sandbox를 활성화한다.
- preload는 명시적으로 허용된 기능만 타입이 지정된 좁은 API로 노출한다.
- renderer가 전달한 파일 경로, 작업 ID와 명령 인자는 main 프로세스와 Python 엔진 경계에서 다시 검증한다.
- Python과 FFmpeg를 실행할 때 셸 명령 문자열을 조합하지 않고 실행 파일과 인자 배열을 분리한다.
- 외부 웹 콘텐츠, CDN 스크립트와 원격 실행 코드는 로드하지 않는다.
- Content Security Policy를 적용하고 로컬 번들 자원만 허용한다.
- 앱 관리 디렉터리 밖의 파일은 명시적인 사용자 선택 없이 수정하거나 삭제하지 않는다.
- 로그에는 스크립트 전문이나 음성 내용 등 불필요한 민감 데이터를 기록하지 않는다.
- 데이터베이스 및 파일 암호화는 단일 사용자 로컬 MVP에서 제외한다. 운영체제 계정과 디스크 보안을 신뢰하며, 외부 사용자 배포 요구가 생기면 재평가한다.

**선택 근거:**

- 미디어 처리에 필요한 운영체제 권한을 main/Python 계층에 제한한다.
- UI 취약점이 임의 파일 접근이나 명령 실행으로 확대되는 것을 방지한다.
- 인증과 암호화 키 관리 등 현재 제품 가치와 무관한 복잡도를 추가하지 않는다.

**영향 범위:** Electron 창 설정, preload 계약, IPC 처리기, 파일 시스템 어댑터, 하위 프로세스 실행기, 로깅.

### API 및 통신 패턴

**결정: Electron과 Python 생성 엔진은 표준 입출력 기반 JSON Lines 프로토콜로 통신한다.**

- Electron main 프로세스가 작업별 Python 엔진 프로세스를 직접 생성한다.
- stdin과 stdout은 한 줄당 하나의 JSON 객체를 전달하는 JSON Lines 프로토콜로 사용한다.
- stderr는 구조화되지 않은 진단 출력으로 분리해 작업 로그에 기록한다.
- 모든 프로토콜 메시지는 `protocolVersion`, `type`, `jobId`, `timestamp`와 메시지별 payload를 포함한다.
- 요청 메시지는 `start`, `cancel` 등 명시적인 명령 타입을 사용한다.
- 이벤트 메시지는 `accepted`, `stage_started`, `progress`, `artifact_created`, `completed`, `failed`, `cancelled` 등 명시적인 이벤트 타입을 사용한다.
- 진행률은 전체 백분율과 현재 단계 식별자를 함께 전달하며, 완료 이벤트 전에는 100%를 보내지 않는다.
- 취소 시 Electron은 먼저 구조화된 `cancel` 명령을 전송하고 제한된 정상 종료 절차를 거친다. 응답하지 않으면 하위 FFmpeg·음성 분석 프로세스까지 포함해 프로세스 트리를 종료한다.
- 각 메시지는 TypeScript와 Python 양쪽에서 동일한 JSON Schema 계약으로 검증한다.
- 프로토콜 호환성이 깨지는 변경은 `protocolVersion`을 올린다.
- renderer는 Python과 직접 통신하지 않고 preload를 거쳐 main 프로세스의 작업 서비스만 호출한다.
- 로컬 HTTP 서버, 포트 할당과 상태 파일 폴링은 사용하지 않는다.

**선택 근거:**

- 네트워크 서버 없이 실시간 진행률, 취소와 순서 있는 이벤트 전달을 지원한다.
- 한 번에 한 작업이라는 MVP 실행 모델과 잘 맞는다.
- JSON Lines 로그를 테스트 픽스처로 재사용할 수 있어 프로세스 간 계약을 검증하기 쉽다.

**영향 범위:** 작업 실행기, Python CLI 진입점, 이벤트 스키마, 진행률 UI, 취소 처리, 오류 매핑, 계약 테스트.

### 프런트엔드 아키텍처

**결정: React UI 상태는 Zustand와 타입 기반의 명시적 작업 상태 머신으로 관리한다.**

- Zustand store는 선택된 게시 날짜, 입력 슬롯, 준비 상태, 최근 작업, 완료 목록, 설정 모달과 현재 실행 상태를 관리한다.
- 장시간 작업 상태는 `idle`, `validating`, `analyzing`, `subtitling`, `composing`, `saving`, `completed`, `failed`, `cancelling`, `cancelled`, `interrupted` 등 명시적인 상태 집합으로 정의한다.
- 모든 상태 변경은 허용된 전이를 검사하는 순수 전이 함수를 통과한다.
- Python 이벤트를 UI 상태로 직접 덮어쓰지 않고 이벤트 어댑터가 도메인 이벤트로 변환한 뒤 전이 함수에 전달한다.
- 작업 실행 중 입력 편집 상태와 실행 중인 작업 스냅샷을 분리한다.
- SQLite의 영구 상태는 main/Python 작업 서비스가 소유하며 Zustand는 UI 투영 상태만 보유한다.
- 완료 목록과 설정은 앱 시작 시 preload API를 통해 로드한다.
- React Router는 사용하지 않고 홈과 사용 가이드의 작은 화면 집합을 앱 수준 뷰 상태로 전환한다.
- 서버 상태 캐시 라이브러리는 사용하지 않는다.

**선택 근거:**

- 단일 창·소수 화면 구조에서 코드량을 작게 유지한다.
- 허용된 상태 전이를 타입과 순수 함수로 강제해 중복 완료, 취소 후 완료와 같은 경합 오류를 방지한다.
- 전용 상태 머신 프레임워크의 추가 학습 및 모델링 비용을 피한다.

**영향 범위:** renderer store, 작업 이벤트 어댑터, 화면 전환, 진행률 표시, 입력 편집 잠금, 상태 단위 테스트.

### 인프라 및 배포

**결정: Python 엔진은 PyInstaller onedir로 동결하고 FFmpeg와 로컬 음성 분석 자원을 Electron 설치 패키지에 포함한다.**

- 사용자는 Python, FFmpeg 또는 별도 Python 패키지를 설치하지 않는다.
- Python 엔진은 PyInstaller 6.21 계열의 onedir 배포물로 생성한다.
- onefile 모드는 시작 시 임시 추출 비용과 장애 분석 난이도 때문에 사용하지 않는다.
- FFmpeg 실행 파일은 검증된 버전과 라이선스 정보를 고정하고 Electron ASAR 외부 리소스로 배치한다.
- 음성 분석 런타임과 모델은 인터넷 없이 실행할 수 있도록 운영체제·CPU 아키텍처별 리소스로 패키징한다.
- Python 엔진, FFmpeg와 음성 분석 실행 파일의 체크섬 및 버전을 빌드 메타데이터에 기록한다.
- electron-builder가 Electron 앱과 외부 실행 리소스를 Windows/macOS 설치 파일로 패키징한다.
- PyInstaller는 교차 컴파일러가 아니므로 Windows 배포물은 Windows 빌드 환경에서, macOS 배포물은 macOS 빌드 환경에서 생성한다.
- macOS는 Apple Silicon을 기본 대상으로 하고 Intel 지원 필요성은 실제 배포 요구가 확인되면 별도 빌드로 추가한다.
- Windows는 x64를 기본 대상으로 한다.
- 코드 서명과 macOS notarization은 타인에게 설치 파일을 배포하기 전에 필수 게이트로 적용한다. 개인 개발 빌드에서는 서명되지 않은 산출물을 허용한다.
- 자동 업데이트는 MVP에서 제외하고 명시적인 설치 파일 교체 방식으로 배포한다.

**선택 근거:**

- 대상 PC의 Python 환경 차이를 제거하고 완전한 오프라인 실행을 보장한다.
- onedir 구조는 대형 모델과 네이티브 라이브러리의 경로를 예측 가능하게 유지하고 문제 진단을 단순화한다.
- 운영체제별 네이티브 미디어 의존성을 각 플랫폼 빌드에서 명시적으로 검증할 수 있다.

**영향 범위:** Python 빌드 스펙, electron-builder 리소스 설정, CI 빌드 매트릭스, 실행 파일 경로 해석, 라이선스 고지, 설치 검증.

### 테스트, 로깅 및 품질 게이트

**결정: 계층별 자동 테스트와 실제 미디어·설치본 검증을 함께 사용한다.**

- React/TypeScript 단위 및 컴포넌트 테스트는 Vitest 4 계열과 React Testing Library를 사용한다.
- Python 생성 엔진의 파서, 타이밍, 자막과 작업 상태 테스트는 pytest를 사용한다.
- TypeScript와 Python은 동일한 JSON Lines 픽스처를 사용해 프로토콜 계약 테스트를 각각 수행한다.
- 작은 라이선스 안전 샘플 미디어로 `스크립트 파싱 → 타이밍 생성 → ASS 생성 → FFmpeg 렌더링` 통합 테스트를 수행한다.
- 데스크톱 핵심 흐름은 Playwright 1.61 계열로 파일 등록, 준비 상태, 생성 진행, 실패, 취소와 완료 목록을 검증한다.
- 작업별 `render_log.txt`에는 단계 시작·종료, 명령 인자에서 민감 정보를 제거한 실행 정보, 처리 시간, 오류 코드와 진단 정보를 기록한다.
- 사용자 UI에는 안정적인 오류 코드와 행동 가능한 메시지만 표시하고 전체 스택 트레이스는 로그에 남긴다.
- Windows/macOS 패키징 결과에서 앱 시작, 포함 바이너리 실행, SQLite 마이그레이션과 샘플 렌더링을 확인하는 설치 스모크 테스트를 수행한다.
- 최종 1080×1920 결과의 자막 위치, 전환, 검은 프레임, 오디오와 기존 CapCut 결과 유사성은 기준 영상과 수동으로 비교한다.
- 영상 품질 기준은 자동 테스트 통과만으로 완료로 판정하지 않는다.

**선택 근거:**

- UI, 프로세스 계약, 미디어 엔진과 패키징 실패를 서로 다른 테스트 계층에서 조기에 분리한다.
- 결정적 데이터 변환은 빠른 단위 테스트로, 코덱·플랫폼 의존 동작은 통합 및 설치 테스트로 검증한다.
- 최종 영상의 미적·청각적 품질은 자동 지표만으로 충분히 판단할 수 없다.

**영향 범위:** CI, 테스트 픽스처, 샘플 미디어, 오류 분류, 진단 로그, 릴리스 체크리스트.

### 결정 우선순위 분석

**구현을 차단하는 핵심 결정:**

- Electron/electron-vite/React/TypeScript 데스크톱 기반
- SQLite 단일 메타데이터 저장소
- 최소 권한 preload/IPC 보안 경계
- JSON Lines 기반 Electron–Python 프로토콜
- 타입 기반 작업 상태 머신
- PyInstaller onedir와 외부 미디어 리소스 패키징

**구조에 큰 영향을 주는 중요 결정:**

- Zustand UI 상태 관리
- 명시적 데이터베이스 마이그레이션
- 임시 결과 생성 후 성공 시 교체하는 재생성 커밋
- 계층별 테스트와 플랫폼별 설치 검증
- 사용자 오류와 기술 진단 로그의 분리

**MVP 이후로 연기한 결정:**

- 인증, 다중 사용자와 권한 관리
- 데이터베이스 및 파일 암호화
- 자동 업데이트
- 클라우드 저장소, 원격 렌더링과 작업 큐
- 작업별 manifest 파일
- Intel macOS 별도 배포
- 복수 작업 대기열과 동시 렌더링

### 결정 영향 분석

**구현 순서:**

1. Electron/electron-vite React/TypeScript 워크스페이스와 Python 패키지를 생성한다.
2. 공유 JSON Schema, 오류 코드와 작업 상태 전이를 정의한다.
3. SQLite 스키마, 마이그레이션과 작업 저장소를 구현한다.
4. Python JSON Lines CLI와 Electron 프로세스 실행기를 구현한다.
5. preload API와 renderer Zustand store를 연결한다.
6. 입력 보관·검증·설정과 완료 목록을 구현한다.
7. 스크립트·음성·자막·FFmpeg 생성 파이프라인을 단계별로 구현한다.
8. 취소, 실패, 비정상 종료와 원자적 재생성을 구현한다.
9. 플랫폼별 PyInstaller/electron-builder 패키징과 설치 테스트를 추가한다.

**컴포넌트 간 의존성:**

- UI 상태 머신은 Python 이벤트 프로토콜과 오류 코드에 의존한다.
- 재생성 안전성은 SQLite 트랜잭션과 임시 출력 디렉터리 정책에 함께 의존한다.
- 완료 목록은 SQLite 기록과 실제 결과 폴더 대조에 의존한다.
- 취소 기능은 Electron 프로세스 실행기와 Python 하위 프로세스 관리가 모두 협력해야 한다.
- 설치 패키징은 Python, FFmpeg, 음성 분석 모델의 플랫폼별 빌드가 완료되어야 검증할 수 있다.

## 구현 패턴 및 일관성 규칙

### 정의된 패턴 범주

**핵심 충돌 지점:** 데이터베이스 명명, TypeScript/Python 명명, 파일 배치, 테스트 위치, 프로세스 메시지 형식, 날짜 형식, 이벤트 이름, 상태 변경, 오류 분류, 로딩 상태, 파일 커밋과 플랫폼 경로 처리 등 12개 영역을 통일한다.

### 명명 패턴

**데이터베이스 명명 규칙:**

- SQLite 테이블, 열, 제약과 인덱스는 `snake_case`를 사용한다.
- 테이블은 복수형 명사를 사용한다. 예: `jobs`, `job_inputs`, `resources`.
- 기본 키는 `id`, 외래 키는 `<단수_테이블명>_id`를 사용한다. 예: `job_id`.
- 인덱스는 `idx_<table>_<columns>` 형식을 사용한다. 예: `idx_jobs_publish_date`.
- 유일 제약은 `uq_<table>_<columns>` 형식을 사용한다.

**API 및 프로토콜 명명 규칙:**

- JSON 필드는 `camelCase`를 사용한다.
- 명령 타입은 현재형 동사 또는 동사구를 사용한다. 예: `start`, `cancel`.
- 이벤트 타입은 이미 발생한 사실을 나타내는 과거형 `snake_case`를 사용한다. 예: `stage_started`, `artifact_created`, `job_completed`.
- preload API는 도메인 동사 중심의 `camelCase` 메서드를 사용한다. 예: `selectInputFiles`, `startJob`, `cancelJob`, `openResultFolder`.

**코드 명명 규칙:**

- TypeScript 변수와 함수는 `camelCase`, 컴포넌트·클래스·타입은 `PascalCase`, 상수는 필요한 경우 `SCREAMING_SNAKE_CASE`를 사용한다.
- React 컴포넌트 파일은 `PascalCase.tsx`를 사용한다. 예: `JobSummary.tsx`.
- 일반 TypeScript 파일은 `kebab-case.ts`를 사용한다. 예: `job-store.ts`.
- Python 변수·함수·모듈은 `snake_case`, 클래스는 `PascalCase`, 상수는 `SCREAMING_SNAKE_CASE`를 사용한다.
- Python 파일은 `snake_case.py`를 사용한다. 예: `job_repository.py`.

### 구조 패턴

**프로젝트 구성:**

- 코드는 기술 종류별 전역 폴더보다 기능 단위로 구성한다.
- renderer 기능은 해당 기능의 컴포넌트, store slice, 어댑터와 테스트를 가까이 둔다.
- React/TypeScript 단위 테스트는 대상 파일 옆에 `*.test.ts` 또는 `*.test.tsx`로 둔다.
- Python 테스트는 엔진의 `tests/` 디렉터리에서 소스 패키지 구조를 반영한다.
- TypeScript/Python 경계의 JSON Schema와 오류 코드는 `packages/contracts`가 소유한다.
- renderer는 main 또는 Python 구현 모듈을 직접 import하지 않는다.
- 공통 유틸리티는 실제로 둘 이상의 기능에서 사용될 때만 공유 폴더로 이동한다.

**파일 구조 패턴:**

- 사용자 데이터 경로와 패키지 리소스 경로를 명시적으로 분리한다.
- 환경별 값은 코드에 하드코딩하지 않고 타입이 지정된 설정 모듈에서 읽는다.
- 플랫폼별 실행 파일 경로는 하나의 리소스 해석 어댑터가 담당한다.
- 데이터베이스 마이그레이션 파일은 순차 번호와 설명을 포함한다. 예: `001_create_jobs.sql`.
- 테스트용 샘플 미디어는 작고 라이선스가 명확한 고정 자산만 사용한다.

### 형식 패턴

**API 응답 형식:**

- preload 호출은 성공 시 필요한 도메인 데이터를 직접 반환하고 실패 시 안정적인 `AppError`를 throw한다.
- `AppError`는 최소 `code`, `message`, `recoverable`, `details` 필드를 가진다.
- renderer에 Python 스택 트레이스나 원시 subprocess 오류를 직접 노출하지 않는다.

**데이터 교환 형식:**

- 프로세스 간 모든 메시지는 다음 공통 envelope를 사용한다.

```json
{
  "protocolVersion": 1,
  "type": "progress",
  "jobId": "uuid",
  "timestamp": "2026-06-19T01:20:30.000Z",
  "payload": {}
}
```

- 게시 날짜는 시간대 없는 `YYYY-MM-DD` 문자열로 교환한다.
- 시각은 UTC ISO 8601 문자열로 교환하고 UI에서만 현지 시간으로 표시한다.
- 누락 가능한 값은 빈 문자열이나 임의 기본값 대신 `null`을 사용한다.
- JSON boolean은 `true`와 `false`만 사용한다.
- SQLite/Python의 `snake_case`와 프로토콜의 `camelCase`는 경계 어댑터에서 명시적으로 변환한다.

### 통신 패턴

**이벤트 시스템 패턴:**

- 이벤트 payload는 이벤트 시점의 사실만 포함하며 UI 표시 문구를 포함하지 않는다.
- 모든 이벤트는 현재 작업을 식별하는 `jobId`를 포함한다.
- 호환성을 깨는 프로토콜 변경은 `protocolVersion`을 올린다.
- 동일 작업에서 `completed`, `failed`, `cancelled` 중 하나의 최종 이벤트만 허용한다.
- 진행률은 단조 증가해야 하며 완료 이벤트 전에 100을 보내지 않는다.

**상태 관리 패턴:**

- Zustand 상태는 공개된 store action 또는 순수 작업 전이 함수로만 변경한다.
- Python 이벤트를 React 컴포넌트에서 직접 해석하지 않는다.
- 이벤트 어댑터가 프로토콜 이벤트를 UI 도메인 이벤트로 변환한다.
- 현재 실행 작업과 `jobId`가 다른 이벤트는 UI 실행 상태에 적용하지 않는다.
- 실행 작업 스냅샷과 사용자가 다음 작업을 위해 편집하는 입력 상태를 분리한다.

### 프로세스 패턴

**오류 처리 패턴:**

- 안정적인 오류 코드 집합을 사용한다.

```text
INPUT_MISSING
INPUT_CONFLICT
SCRIPT_INVALID
PRAYER_BOUNDARY_AMBIGUOUS
RESOURCE_INVALID
PROCESS_FAILED
OUTPUT_COMMIT_FAILED
JOB_INTERRUPTED
```

- Python은 기술 원인과 진단 컨텍스트를 로그에 기록한다.
- main 프로세스는 기술 오류를 안정적인 애플리케이션 오류로 매핑한다.
- renderer는 오류 코드에 대응하는 사용자 행동과 메시지를 표시한다.
- 예외를 무시하거나 단순 문자열 오류만 전달하지 않는다.
- MVP에서는 자동 재시도를 구현하지 않는다.

**로딩 상태 패턴:**

- 전역 `isLoading` 하나로 모든 비동기 상태를 표현하지 않는다.
- 파일 등록, 스크립트 검증, 설정 교체와 생성 단계의 상태를 분리한다.
- 진행 중 표시에는 단계명과 백분율 또는 처리 항목 수를 함께 제공한다.
- 취소 요청 중에는 `cancelling` 상태를 사용하고 취소 완료 전까지 새 작업을 시작하지 않는다.

**파일 안전 패턴:**

- 드롭한 원본 파일을 직접 수정하거나 삭제하지 않는다.
- 최종 경로에 직접 렌더링하지 않는다.
- 작업별 임시 디렉터리에서 생성한 결과를 검증한 후 성공 시 최종 위치로 교체한다.
- 파일 제거 전 대상이 애플리케이션 관리 루트 내부인지 확인한다.
- 경로 문자열을 수동 연결하지 않고 각 언어의 경로 API를 사용한다.

### 강제 지침

**모든 AI 구현 에이전트는 반드시:**

- 공유 계약, 오류 코드와 상태 전이를 먼저 확인한다.
- 새 이벤트·오류 코드·DB 변경 시 계약과 테스트를 함께 수정한다.
- renderer에서 파일 시스템이나 프로세스 API를 직접 호출하지 않는다.
- 사용자 메시지와 기술 진단 로그를 분리한다.
- 플랫폼별 경로와 실행 파일 차이를 어댑터 뒤에 격리한다.
- 기존 아키텍처 규칙을 변경해야 하면 구현 전에 이 문서를 갱신한다.

**패턴 집행:**

- TypeScript 린트·포맷·타입 검사와 Python 린트·테스트를 CI에서 실행한다.
- JSON Schema 계약 테스트를 TypeScript와 Python 양쪽에서 실행한다.
- SQLite 마이그레이션을 빈 DB와 이전 버전 DB에 적용하는 테스트를 유지한다.
- 패턴 위반을 발견하면 해당 코드와 함께 회귀 테스트를 추가한다.

### 패턴 예시

**좋은 예:**

- `jobs.publish_date`를 저장하고 프로토콜에서는 `publishDate`로 변환한다.
- Python의 `stage_started` 이벤트를 renderer 어댑터가 `onStageStarted` 동작으로 변환한다.
- `OUTPUT_COMMIT_FAILED` 오류가 기존 완료 결과를 유지한 채 사용자에게 결과 교체 실패를 안내한다.

**금지할 예:**

- renderer에서 `fs.unlink` 또는 `child_process.spawn`을 직접 호출한다.
- 한 기능은 `jobId`, 다른 기능은 `job_id`를 같은 JSON 경계에서 사용한다.
- Python stdout에 일반 로그와 JSON 프로토콜 메시지를 섞어 쓴다.
- 작업 상태를 임의 문자열로 추가하거나 완료 후 진행 이벤트를 적용한다.
- 기존 완료 파일 위에 FFmpeg 출력을 직접 기록한다.

## 프로젝트 구조 및 경계

### 전체 프로젝트 디렉터리 구조

```text
gracetree-shorts-studio/
├── package.json
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── README.md
├── apps/
│   └── desktop/
│       ├── package.json
│       ├── electron.vite.config.ts
│       ├── electron-builder.yml
│       ├── vitest.config.ts
│       └── src/
│           ├── main/
│           │   ├── index.ts
│           │   ├── ipc/
│           │   │   ├── register-job-handlers.ts
│           │   │   ├── register-file-handlers.ts
│           │   │   └── register-resource-handlers.ts
│           │   ├── jobs/
│           │   │   ├── job-service.ts
│           │   │   ├── engine-process.ts
│           │   │   ├── event-adapter.ts
│           │   │   └── process-tree.ts
│           │   ├── files/
│           │   │   ├── file-dialogs.ts
│           │   │   ├── open-folder.ts
│           │   │   └── managed-paths.ts
│           │   └── resources/
│           │       └── resource-paths.ts
│           ├── preload/
│           │   ├── index.ts
│           │   └── desktop-api.ts
│           └── renderer/
│               ├── index.html
│               ├── src/
│               │   ├── main.tsx
│               │   ├── App.tsx
│               │   ├── styles/
│               │   │   ├── tokens.css
│               │   │   └── globals.css
│               │   ├── features/
│               │   │   ├── job-editor/
│               │   │   ├── job-progress/
│               │   │   ├── job-history/
│               │   │   ├── resources/
│               │   │   └── guide/
│               │   └── shared/
│               │       ├── components/
│               │       ├── hooks/
│               │       └── accessibility/
│               └── assets/
├── packages/
│   └── contracts/
│       ├── package.json
│       ├── schemas/
│       │   ├── engine-command.schema.json
│       │   ├── engine-event.schema.json
│       │   └── app-error.schema.json
│       ├── src/
│       │   ├── protocol.ts
│       │   ├── errors.ts
│       │   ├── job-state.ts
│       │   └── desktop-api.ts
│       └── fixtures/
├── engine/
│   ├── pyproject.toml
│   ├── gracetree_engine/
│   │   ├── __main__.py
│   │   ├── cli.py
│   │   ├── protocol/
│   │   ├── jobs/
│   │   ├── storage/
│   │   ├── inputs/
│   │   ├── scripts/
│   │   ├── speech/
│   │   ├── subtitles/
│   │   ├── media/
│   │   └── diagnostics/
│   ├── migrations/
│   │   └── 001_create_jobs.sql
│   ├── tests/
│   └── packaging/
│       └── gracetree-engine.spec
├── resources/
│   ├── ffmpeg/
│   │   ├── windows-x64/
│   │   └── macos-arm64/
│   ├── speech-models/
│   └── licenses/
├── tests/
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   │   ├── media/
│   │   └── protocol/
│   └── smoke/
├── scripts/
│   ├── build-engine.mjs
│   ├── build-desktop.mjs
│   └── verify-package.mjs
└── .github/
    └── workflows/
        ├── ci.yml
        └── release.yml
```

### 아키텍처 경계

**API 경계:**

- renderer는 preload가 제공하는 `desktopApi`만 호출한다.
- preload API는 파일 선택, 작업 조회·실행·취소, 공통 리소스 관리와 결과 폴더 열기로 제한한다.
- main 프로세스는 renderer 요청을 검증하고 Python 엔진 명령으로 변환한다.
- Python 엔진은 외부 HTTP API를 제공하지 않고 JSON Lines 표준 입출력 계약만 제공한다.

**컴포넌트 경계:**

- `job-editor`는 게시 날짜, 파일 슬롯, 준비 상태와 생성 시작을 소유한다.
- `job-progress`는 현재 작업 상태 머신, 단계·진행률과 결과 모달을 소유한다.
- `job-history`는 완료 목록, 최근 선택 작업과 결과 폴더 상태를 소유한다.
- `resources`는 공통 영상, 기본 BGM과 폰트의 표시·교체 흐름을 소유한다.
- `guide`는 정적 도움말 화면을 소유한다.
- 기능 간 공유는 Zustand의 명시적 selector와 action을 통해서만 수행한다.

**서비스 경계:**

- Electron main의 `job-service`는 renderer 요청과 Python 프로세스 수명주기를 조정한다.
- `engine-process`는 JSON Lines 송수신과 프로세스 종료만 담당하며 도메인 규칙을 구현하지 않는다.
- Python `jobs`는 작업 오케스트레이션과 상태 전이를 담당한다.
- `inputs`, `scripts`, `speech`, `subtitles`, `media`는 각각 하나의 생성 단계 책임을 갖는다.
- `storage`만 SQLite에 접근하며 다른 Python 모듈은 repository 인터페이스를 사용한다.

**데이터 경계:**

- SQLite는 작업 메타데이터와 완료 이력의 유일한 기준이다.
- 파일 시스템은 입력 사본, 공통 리소스와 생성 산출물의 기준이다.
- 앱 시작 시 저장소 계층이 SQLite 기록과 실제 경로 존재 여부를 대조한다.
- renderer에는 필요한 표시 데이터만 DTO로 전달하고 데이터베이스 행을 그대로 노출하지 않는다.

### 요구사항과 구조 매핑

**입력 등록 및 설정 — FR-1~FR-10**

- UI: `apps/desktop/src/renderer/src/features/job-editor/`, `features/resources/`
- OS 통합: `apps/desktop/src/main/files/`, `src/main/resources/`
- 엔진: `engine/gracetree_engine/inputs/`, `storage/`

**영상 생성 — FR-11~FR-16**

- 스크립트: `engine/gracetree_engine/scripts/`
- 음성 분석: `engine/gracetree_engine/speech/`
- 자막: `engine/gracetree_engine/subtitles/`
- FFmpeg 합성: `engine/gracetree_engine/media/`
- 작업 오케스트레이션: `engine/gracetree_engine/jobs/`

**진행 및 취소 — FR-17~FR-19**

- UI: `features/job-progress/`
- 프로세스 관리: `apps/desktop/src/main/jobs/`
- 엔진 취소 처리: `engine/gracetree_engine/jobs/`
- 계약: `packages/contracts/`

**완료 및 오류 — FR-20~FR-21**

- 결과 모달: `features/job-progress/`
- 오류 매핑: `packages/contracts/src/errors.ts`, `engine/gracetree_engine/diagnostics/`
- 작업 로그: 사용자 데이터의 작업별 `output/render_log.txt`

**완료 목록 및 폴더 열기 — FR-22~FR-24**

- UI: `features/job-history/`
- 조회: Python `storage/`
- 폴더 열기: Electron main `files/open-folder.ts`

### 통합 지점

**내부 통신:**

- renderer → preload: 타입이 지정된 비동기 메서드와 작업 이벤트 구독
- preload → main: Electron IPC
- main → Python: JSON Lines stdin/stdout
- Python → FFmpeg·음성 분석: 인자 배열 기반 하위 프로세스
- Python → SQLite: repository와 명시적 트랜잭션

**외부 통합:**

- MVP에는 네트워크 기반 외부 서비스가 없다.
- 운영체제 통합은 파일 선택기, Explorer/Finder 폴더 열기와 앱 데이터 디렉터리 사용으로 제한한다.

**데이터 흐름:**

```text
Renderer
→ Preload API
→ Electron Main
→ Python JSON Lines Process
→ SQLite / FFmpeg / Local Speech Analysis
→ Structured Events
→ Electron Main
→ Renderer State Machine
```

### 사용자 데이터 디렉터리

```text
GraceTreeData/
├── studio.db
├── resources/
│   ├── intro.mp4
│   ├── prayer-loop.mp4
│   ├── default-bgm.mp3
│   └── subtitle-font.ttf
├── jobs/
│   └── 2026-06-20/
│       ├── input/
│       │   ├── thumbnail.png
│       │   ├── voice.m4a
│       │   ├── script.txt
│       │   └── bgm.mp3
│       ├── output/
│       │   ├── final.mp4
│       │   ├── subtitles.ass
│       │   ├── timing.json
│       │   └── render_log.txt
│       ├── temp/
│       └── logs/
│           └── <attempt-id>-render_log.txt
└── logs/
    └── app.log
```

- `input`은 사용자가 등록한 원본의 앱 관리 사본을 보관한다.
- `output`은 최종 영상과 사용자가 확인할 보존 산출물을 보관한다.
- `temp`는 음성 변환, 배경 영상 조립과 `final.pending.mp4` 등 생성 중 임시 파일만 보관한다.
- `temp`의 결과를 검증한 후에만 `output`으로 커밋한다.
- 성공·실패·취소 후 `temp`를 정리한다.
- 모든 실행 시도 로그는 `logs/<attempt-id>-render_log.txt`에 보존한다.
- 성공한 실행의 로그는 `output/render_log.txt`에도 복사한다.
- 별도 `work` 디렉터리는 사용하지 않는다.

### 파일 구성 패턴

**설정 파일:**

- TypeScript 공통 설정은 루트에, 앱별 빌드 설정은 `apps/desktop`에 둔다.
- Python 의존성과 도구 설정은 `engine/pyproject.toml`이 소유한다.
- 패키징 대상과 외부 리소스 경로는 electron-builder와 PyInstaller 설정에 명시한다.

**소스 구성:**

- renderer는 기능 단위, main은 운영체제·작업 서비스 단위, Python은 생성 단계 단위로 구성한다.
- 계약은 구현과 분리해 두 언어가 독립적으로 검증할 수 있게 한다.

**테스트 구성:**

- TypeScript 단위 테스트는 소스와 함께 둔다.
- Python 단위 테스트는 `engine/tests`에 둔다.
- 언어·프로세스를 넘는 테스트는 루트 `tests/integration`, 실제 앱 흐름은 `tests/e2e`, 설치 검증은 `tests/smoke`에 둔다.

**자산 구성:**

- 개발·배포용 실행 자산은 루트 `resources`에 운영체제별로 둔다.
- 사용자 공통 리소스는 실행 시 사용자 데이터 `resources`로 복사·관리한다.
- 테스트 자산은 제품 리소스와 분리한다.

### 개발 워크플로 통합

**개발 실행:**

- 루트 워크스페이스 명령이 contracts 빌드, Python 개발 환경과 Electron 개발 서버를 조정한다.
- 개발 환경에서는 Python 모듈을 직접 실행하고 배포 환경에서는 PyInstaller 실행 파일을 사용한다.

**빌드:**

- contracts 생성·검증 → Python 테스트·PyInstaller → Electron 빌드·테스트 → electron-builder 순서로 실행한다.
- 플랫폼별 빌드가 해당 플랫폼 FFmpeg와 음성 분석 자원을 포함하는지 검증한다.

**배포:**

- Windows x64와 macOS arm64 릴리스 작업을 분리한다.
- 설치 후 스모크 테스트에서 앱 시작, 사용자 데이터 초기화, 마이그레이션, 포함 바이너리 실행과 샘플 렌더링을 확인한다.

## 아키텍처 검증 결과

### 일관성 검증 ✅

**결정 호환성:**

- Electron main/preload/renderer 분리와 JSON Lines Python 엔진 경계가 서로 충돌하지 않는다.
- Python 표준 `sqlite3`, faster-whisper와 FFmpeg는 PyInstaller onedir 배포 방식과 호환된다.
- renderer의 최소 권한 모델은 Zustand UI 상태와 preload API 구조를 지원한다.
- SQLite 트랜잭션과 임시 출력 커밋 전략이 재생성 안전성 요구를 함께 충족한다.

**패턴 일관성:**

- SQLite/Python의 `snake_case`, TypeScript/JSON의 `camelCase` 경계가 명시되어 있다.
- 이벤트, 오류 코드, 상태 전이와 최종 상태 규칙이 하나의 계약 패키지로 통합된다.
- 파일 안전, 취소와 오류 처리 규칙이 데이터·통신·프로젝트 구조 전반에서 동일하다.

**구조 정렬:**

- renderer, preload, main, contracts와 Python 엔진의 물리적 구조가 책임 경계를 반영한다.
- 모든 SQLite 접근은 Python storage 계층으로 제한된다.
- 테스트, 패키징 자산과 사용자 데이터가 제품 소스와 명확히 분리된다.

### 요구사항 범위 검증 ✅

**기능 범위:**

- FR-1~FR-10은 job editor, resource settings, main 파일 어댑터와 Python inputs/storage가 지원한다.
- FR-11~FR-16은 scripts, speech, subtitles, media와 jobs 오케스트레이터가 지원한다.
- FR-17~FR-19는 작업 상태 머신, JSON Lines 이벤트와 프로세스 트리 취소가 지원한다.
- FR-20~FR-21은 결과 모달, 안정적인 오류 코드와 작업별 진단 로그가 지원한다.
- FR-22~FR-24는 SQLite 완료 이력, 실제 경로 대조와 운영체제 폴더 열기가 지원한다.

**비기능 범위:**

- 로컬 처리: 외부 네트워크 서비스 없이 패키징된 실행 자원만 사용한다.
- 신뢰성: 원본 불변, 임시 출력, 성공 후 커밋과 시도별 로그 보존을 적용한다.
- 복구: 앱 시작 시 실행 중 상태를 `interrupted`로 정리하고 입력과 기존 결과를 유지한다.
- 접근성: React 컴포넌트 계층에서 키보드, 포커스, live region과 디자인 토큰 계약을 적용한다.
- 성능: UI 이벤트는 JSON Lines 스트림으로 1초 이내 갱신할 수 있다. 기준 PC의 렌더링 목표는 구현 성능 측정 후 확정한다.
- 확장성: UI, 작업 실행, 저장소와 영상 생성 단계를 독립 경계로 분리하되 MVP에 분산 인프라를 추가하지 않는다.

### 구현 준비성 검증 ✅

**결정 완전성:**

- 핵심 런타임, 저장소, 통신, 상태 관리, 보안, 패키징과 테스트 결정이 문서화됐다.
- 현재 확인된 기준 버전은 pnpm 11.8, Zustand 5.0.14, faster-whisper 1.2.1, PyInstaller 6.21.0, Vitest 4 계열과 Playwright 1.61 계열이다.
- 실제 구현 시 lockfile과 Python lock 파일로 정확한 의존 버전을 고정한다.

**구조 완전성:**

- 구현 파일과 디렉터리, 사용자 데이터 구조, 테스트와 배포 구조가 구체적으로 정의됐다.
- FR 범주가 구현 위치에 매핑됐다.
- 프로세스 및 데이터 통합 경계가 명확하다.

**패턴 완전성:**

- 이름, 파일 배치, JSON 형식, 이벤트, 상태, 오류, 로딩과 파일 안전 패턴이 정의됐다.
- 좋은 예와 금지 예가 포함됐다.
- 타입 검사, 린트, 계약 테스트와 마이그레이션 테스트로 규칙을 집행한다.

### 검증 중 보완한 사항

**Python 엔진 수명주기:**

- Electron 앱이 시작되면 장기 실행 Python 엔진 프로세스 하나를 시작한다.
- 이 프로세스가 SQLite 조회, 설정 검증과 생성 작업 명령을 처리한다.
- MVP에서는 엔진 프로세스당 실행 중 생성 작업을 하나로 제한한다.
- 엔진이 비정상 종료되면 main은 현재 작업을 `interrupted`로 표시하고 필요 시 엔진을 다시 시작한다. 실행 중 작업을 자동 재시도하지 않는다.

**실행 시도별 로그:**

- 모든 생성 시도는 고유한 `attemptId`를 갖는다.
- 성공, 실패와 취소 로그를 `jobs/<publish-date>/logs/<attempt-id>-render_log.txt`에 보존한다.
- 성공한 시도의 로그는 `output/render_log.txt`에도 복사한다.
- 재생성 실패 로그가 기존 성공 결과와 성공 로그를 덮어쓰지 않는다.

**도구 및 스타일 규칙:**

- Node 패키지 관리자는 pnpm 11.8 계열을 사용한다.
- Zustand 5.0.14 계열을 사용한다.
- UX 디자인 토큰은 전역 CSS custom properties로 정의하고 기능별 스타일은 CSS Modules를 사용한다.
- 로컬 음성 분석 구현은 faster-whisper 1.2.1 계열을 사용한다.
- 음성 모델 크기, 양자화와 CPU thread 설정은 기준 PC의 한국어 정확도·처리 시간 측정 후 고정한다.

### 공백 분석

**치명적 공백:** 없음.

**중요 공백:**

- 기준 Windows/macOS 장비 사양과 허용 렌더링 시간 목표가 미확정이다. 첫 수직 슬라이스에서 실제 샘플 영상으로 측정해 성능 예산을 추가한다.
- 음성 모델 설정은 동일한 기준 샘플에서 자막 싱크 성공률과 처리 시간을 비교한 뒤 고정한다.

**선택적 개선:**

- 공개 배포 전 코드 서명, notarization과 라이선스 고지 자동 검증을 강화할 수 있다.
- 실제 외부 사용자 요구가 확인되면 Intel macOS 빌드와 자동 업데이트를 추가할 수 있다.

### 아키텍처 완전성 체크리스트

**요구사항 분석**

- [x] 프로젝트 컨텍스트를 충분히 분석함
- [x] 규모와 복잡도를 평가함
- [x] 기술적 제약을 식별함
- [x] 횡단 관심사를 매핑함

**아키텍처 결정**

- [x] 핵심 결정을 버전과 함께 문서화함
- [x] 기술 스택을 지정함
- [x] 통합 패턴을 정의함
- [x] 성능 고려사항과 측정 게이트를 정의함

**구현 패턴**

- [x] 명명 규칙을 수립함
- [x] 구조 패턴을 정의함
- [x] 통신 패턴을 지정함
- [x] 프로세스 패턴을 문서화함

**프로젝트 구조**

- [x] 전체 디렉터리 구조를 정의함
- [x] 컴포넌트 경계를 수립함
- [x] 통합 지점을 매핑함
- [x] 요구사항과 구조 매핑을 완료함

### 아키텍처 준비도 평가

**전체 상태:** 구현 준비 완료

**신뢰 수준:** 높음

**핵심 강점:**

- UI와 로컬 미디어 엔진의 명확한 보안·프로세스 경계
- 기존 결과를 보호하는 원자적 파일 커밋과 SQLite 트랜잭션
- 두 언어가 공유하는 버전형 프로토콜과 오류 계약
- FR 전체를 구체적인 모듈과 테스트 위치에 연결한 구조

**향후 개선 영역:**

- 기준 장비별 성능 예산
- 한국어 음성 모델의 최종 크기와 실행 설정
- 외부 배포를 위한 서명·업데이트 및 추가 플랫폼 지원

### 구현 인계

**AI 에이전트 지침:**

- 이 문서의 아키텍처 결정, 구현 패턴과 프로젝트 경계를 그대로 따른다.
- 새 이벤트, 오류 코드, DB 스키마 또는 경계 변경은 계약·테스트·문서를 함께 변경한다.
- 구현 편의를 이유로 renderer에 파일 시스템·프로세스 권한을 추가하지 않는다.
- 최종 영상 품질은 자동 테스트와 기준 영상 수동 비교를 모두 통과해야 한다.

**첫 구현 우선순위:**

```bash
npm create @quick-start/electron@latest apps/desktop -- --template react-ts
```

이후 pnpm 워크스페이스, `packages/contracts`와 Python 엔진 패키지를 생성하고 가장 작은 수직 슬라이스인 `작업 생성 → JSON Lines 이벤트 → SQLite 기록 → 완료 목록 표시`를 구현한다.
