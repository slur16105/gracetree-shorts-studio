---
name: GraceTree Mono Focus
description: 말씀기도 쇼츠 제작 데스크톱 앱의 UI 재디자인 — 거의 무채색 다크 표면 + 단일 인디고 액센트(Mono Focus). 기존 마크업·CSS모듈 구조 위에서 비주얼/레이아웃만 개선.
status: final
created: 2026-06-27
updated: 2026-06-28
sources:
  - ../ux-gracetree-shorts-studio-2026-06-19/DESIGN.md
  - ../ux-gracetree-shorts-studio-2026-06-19/EXPERIENCE.md
colors:
  base: '#0A0A0B'
  nav: '#0C0C0D'
  panel: '#0F0F10'
  raised: '#18181A'
  hover: '#202023'
  selected: '#262629'
  text-primary: '#F3F3F4'
  text-secondary: '#9C9CA1'
  text-disabled: '#66666B'
  border: '#2A2A2D'
  border-strong: '#5C5C61'
  accent: '#7C84E8'
  progress: '#9AA0F2'
  warning: '#F2B84B'
  danger: '#F05D5E'
  primary-action: '#F3F3F4'
  primary-action-foreground: '#0A0A0B'
  focus: '#7DD3FC'
typography:
  title-lg:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.25'
    letterSpacing: -0.02em
  title-md:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 20px
    fontWeight: '700'
    lineHeight: '1.35'
    letterSpacing: -0.01em
  title-sm:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 16px
    fontWeight: '600'
    lineHeight: '1.4'
  body:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.55'
  label:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 13px
    fontWeight: '600'
    lineHeight: '1.4'
  meta:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
  eyebrow:
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: 0.09em
rounded:
  sm: 8px
  md: 12px
  lg: 18px
  xl: 20px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 20px
  '6': 24px
  '7': 32px
  '8': 40px
  sidebar-width: 78px
  status-height: 70px
components:
  sidebar-icon-button:
    size: 44px
    radius: '{rounded.md}'
    foreground: '{colors.text-secondary}'
    hover-foreground: '{colors.text-primary}'
    hover-background: '{colors.raised}'
    active-foreground: '{colors.text-primary}'
    active-border: '{colors.accent}'
    active-background: '{colors.selected}'
    active-bar: '{colors.accent}'
  brand-mark:
    size: 44px
    radius: '{rounded.md}'
    background: '{colors.raised}'
    border: '{colors.border}'
    glyph: sprout
    glyph-size: 28px
    glyph-color: '{colors.accent}'
  drop-zone:
    background: '{colors.panel}'
    border: '{colors.border-strong}'
    radius: '{rounded.lg}'
    drag-active-border: '{colors.accent}'
    drag-active-background: '{colors.raised}'
  file-slot:
    background: '{colors.raised}'
    border: '{colors.border}'
    radius: '{rounded.md}'
    ready-border: '{colors.progress}'
    attention-border: '{colors.warning}'
    invalid-border: '{colors.danger}'
  readiness-progress:
    track: '{colors.border}'
    fill: '{colors.progress}'
    height: 8px
  primary-button:
    background: '{colors.primary-action}'
    foreground: '{colors.primary-action-foreground}'
    radius: '{rounded.full}'
  secondary-button:
    background: '{colors.raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border-strong}'
    radius: '{rounded.full}'
  date-picker:
    trigger-background: '{colors.raised}'
    trigger-border: '{colors.border}'
    radius: '{rounded.md}'
  calendar-popover:
    background: '{colors.raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border}'
    today-border: '{colors.border-strong}'
    selected-background: '{colors.accent}'
    selected-foreground: '{colors.base}'
    radius: '{rounded.lg}'
  completion-row:
    background: '{colors.raised}'
    border: '{colors.border}'
    selected-border: '{colors.accent}'
    selected-background: '{colors.selected}'
    radius: '{rounded.md}'
  bottom-status-bar:
    background: '{colors.panel}'
    border-top: '{colors.border}'
    height: '{spacing.status-height}'
    idle-dot: '{colors.text-secondary}'
    running-dot: '{colors.progress}'
  resource-settings-dialog:
    background: '{colors.raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
  guide-card:
    background: '{colors.panel}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
    eyebrow-color: '{colors.text-secondary}'
  result-dialog:
    background: '{colors.raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border}'
    radius: '{rounded.lg}'
---

## Brand & Style

GraceTree Mono Focus는 영상 편집기가 아니라 반복 제작을 차분하게 끝내는 로컬 작업 도구다. 화면의 주인공은 시각 장식이 아니라 사용자의 파일명, 스크립트 제목, 게시 날짜, 생성 상태다. 그래서 색을 거의 빼고 거의 무채색 다크 표면 위에 텍스트와 상태만 또렷하게 남긴다.

색은 단 한 계열, 인디고만 쓴다. 인디고는 두 가지 의미로만 등장한다 — **사용자가 직접 고른 지점**(`{colors.accent}`)과 **시스템의 준비·진행·성공 신호**(`{colors.progress}`). 그 외 모든 면은 무채색이며, 실패와 경고만 빨강·앰버로 깨뜨린다. 종교적 장식은 전면에 내세우지 않는다. 브랜드 마크인 "땅에서 돋는 새싹"이 은혜가 자라는 정서를 조용히 담는다.

이 문서는 06-19 "Studio Black"의 정보 구조와 운영 원칙을 계승하되, 핫핑크+그린 이원 액센트를 단일 인디고로 통합한 재디자인이다. 기존 마크업·클래스·CSS모듈(`*.module.css`) 구조는 유지하고, 토큰·색·타이포·간격·정렬만 이 문서에 맞춘다.

## Colors

- `{colors.base}`는 앱의 최하단 캔버스, `{colors.nav}`는 사이드바, `{colors.panel}`은 드롭존·카드·상태바, `{colors.raised}`는 파일 슬롯·목록 행·모달의 표면이다. `{colors.hover}`와 `{colors.selected}`는 hover와 선택 상태를 한 단계씩 밝혀 위계를 만든다.
- `{colors.text-primary}`는 제목과 주요 동작, `{colors.text-secondary}`는 파일 설명·날짜·보조 상태, `{colors.text-disabled}`는 비활성 텍스트에 쓴다. 비활성 텍스트는 정보를 전달하는 유일한 수단으로 사용하지 않는다.
- `{colors.border}`는 기본 1px 경계, `{colors.border-strong}`는 드롭존·보조 버튼처럼 강조가 필요한 경계에 쓴다.
- **`{colors.accent}`(인디고)는 사용자가 고르거나 현재 위치한 지점에만 쓴다** — 브랜드 마크, 활성 내비게이션, 달력 선택일, 선택된 완료 행, 드래그 진입 경계, 동작 가능한 인라인 링크. 그 외에는 절대 쓰지 않는다.
- **`{colors.progress}`(밝은 인디고)는 시스템 상태에만 쓴다** — 입력 준비율 막대, 충족된 입력 슬롯, 생성 성공, 실행 중 상태 점. 녹색을 대체하는 단일 진행색이다.
- `{colors.warning}`은 확인이 필요한 입력과 중단 가능 상태, `{colors.danger}`는 실패와 파괴적 확인에만 쓴다. 이 둘은 무채색·인디고로 흐리지 않는다.
- 주요 본문 조합은 WCAG 2.2 AA 일반 텍스트 대비 4.5:1 이상을 목표로 한다. 밝은 인디고 위 텍스트나 인디고 채움 위 텍스트는 `{colors.base}` 등 어두운 전경으로 4.5:1을 유지한다.

> **선택색과 진행색이 같은 인디고 계열이라는 점에 주의한다.** 한 화면에서 둘이 가까이 놓일 때(예: 선택된 완료 행 + 그 행의 진행 표시)는 명도 차이(`accent` vs 밝은 `progress`)와 형태 차이(경계 vs 채움)로 구분한다.

## Typography

Windows·macOS에서 동일한 밀도를 유지하도록 Pretendard를 우선하고, 없으면 플랫폼 시스템 산세리프로 대체한다. (코드 적용 시 Pretendard 웹폰트 번들 여부를 확인한다.)

- 화면 제목 `<h1>`은 `{typography.title-lg}`(28px). 섹션 제목 `<h2>`는 `{typography.title-md}`, 카드·하위 제목 `<h3>`는 `{typography.title-sm}`.
- 파일명·버튼·라벨은 `{typography.label}`, 설명·오류 해결 문장은 `{typography.body}`.
- 게시일·실제 생성일·진행 보조 정보는 `{typography.meta}`.
- 영문 대문자 안내(eyebrow)는 화면당 하나 이하로 제한하고 `{typography.eyebrow}`를 무채색(`{colors.text-secondary}`)으로 쓴다.

폰트 크기는 위 토큰으로만 표현하고, 컴포넌트 CSS에 px를 하드코딩하지 않는다. 작업 제목은 `script.txt`의 `[제목]` 줄바꿈을 공백으로 합쳐 한 줄로 표시하고, 목록에서는 말줄임을 허용하되 전체 제목을 툴팁·접근성 이름으로 제공한다.

## Layout & Spacing

기본 창은 데스크톱 가로형이며 권장 최소 콘텐츠 크기는 1180×720이다. 홈 레이아웃은 "헤더 + 2-pane + 푸터"로 재구성한다(레이아웃 A). 시각 참고: [홈 레이아웃 A](mockups/home-layout-A.html).

- 전역 사이드바: `{spacing.sidebar-width}`(78px). 하단 상태 바: `{spacing.status-height}`(70px)로 고정. macOS는 `titleBarStyle: hiddenInset`으로 다크 콘텐츠가 최상단까지 올라오고, 신호등 자리만큼 사이드바 위쪽을 비운다(사이드바는 창 드래그 영역).
- **헤더 바** — 본문 최상단 전체 폭. eyebrow + 화면 제목(`영상 작업`)만 둔다. 날짜·생성 버튼은 헤더에 두지 않는다.
- **본문 2-pane** — 왼쪽 입력 영역 `minmax(440px, 1fr)`, 오른쪽 사이드 열 `minmax(280px, 360px)`.
  - 왼쪽: 최상단 한 줄에 **게시일 picker(좌) + 영상 생성 버튼(우)**, 그 아래 드롭존 + 파일 슬롯. 워크스페이스 제목(라벨)은 두지 않는다.
  - 오른쪽: **입력 준비 카드**(위) + **완료 목록**(아래).
- **푸터(상태 바)** — 본문 2-pane와 정렬한다. 왼쪽은 `현재 작업: <제목>`(상태 점 포함), 오른쪽은 **생성 진행률 바 하나만** 두고 그 폭을 오른쪽 완료 목록 열 폭에 맞춘다. 세로 구분선·중복 텍스트는 두지 않는다.
- 간격은 4·8·12·16·20·24·32·40 스케일(`{spacing.1}`~`{spacing.8}`)만 쓴다. 주요 컨테이너 바깥 패딩은 `{spacing.8}`(40px)로 통일하고, 행 내부는 `{spacing.3}`~`{spacing.4}`를 쓴다.
- 창이 좁아져도 완료 목록은 사라지지 않으며, 최소 창 폭에서 좌우 패널의 최소 폭을 유지한다. 모바일 레이아웃은 제공하지 않는다.

## Elevation & Depth

기본 화면은 그림자보다 표면 색(base→nav→panel→raised)과 1px 경계로 깊이를 만든다. 달력 팝오버와 설정·결과 모달만 배경 위에 뜨는 요소이므로 넓고 낮은 불투명도의 그림자를 허용한다. 중첩 모달은 금지한다.

## Shapes

도구형 화면의 선명함을 유지하면서 딱딱하지 않도록 8/12/18/20px 반경을 쓴다.

- 주요·보조 버튼은 `{rounded.full}`(알약형)을 쓴다.
- 목록 행·파일 슬롯·작은 버튼·카드는 `{rounded.md}`(12px).
- 큰 드롭 영역·빈 상태·모달·팝오버는 `{rounded.lg}`(18px).
- 인라인 코드·작은 칩은 `{rounded.sm}`(8px).

## Components

- **Sidebar Icon Button** — 44×44px. 홈, 사용 가이드, 공통 리소스 설정을 제공한다. 활성 항목은 `{colors.selected}` 배경, `{colors.accent}` 경계, `{colors.text-primary}` 아이콘, 왼쪽 `{colors.accent}` 바를 쓴다. hover는 `{colors.raised}` 배경.
- **Brand Mark** — 44×44 박스(`{colors.raised}` 표면 + `{colors.border}`) 안에 24px 새싹 글리프를 `{colors.accent}`로 표시한다. 브랜드는 인디고가 상주하는 유일한 지점이다. 글리프(viewBox 0 0 32 32, `currentColor` 모노라인):
  ```
  M16 24 V12.5
  M16 18 C11.4 18 9.2 14.4 10.2 9.6 C14.8 10.5 16 14.4 16 18 Z
  M16 14.8 C20.6 14.8 22.8 11.2 21.8 6.4 C17.2 7.3 16 11.2 16 14.8 Z
  M7 24 Q16 20.5 25 24
  ```
- **Drop Zone** — 큰 점선 경계(`{colors.border-strong}`)와 중앙 안내. 드래그 진입 시 경계를 `{colors.accent}`로 바꾸고 표면을 `{colors.raised}`로 한 단계 밝힌다. 등록 후에는 파일 슬롯을 내부에 표시한다.
- **File Slot** — 역할·파일명·상태를 한 행에 표시한다. 충족(ready)은 `{colors.progress}` 경계, 확인 필요(conflict/missing)는 `{colors.warning}`, 오류(invalid)는 `{colors.danger}`. 색과 함께 아이콘·문구를 제공한다.
  - **삭제(✕)**: 파일명 요소 안, 제목 바로 우측에 인라인으로 둔다. 평소 `{colors.text-disabled}`, hover/focus 시 `{colors.danger}`.
  - **다시 선택**: 행 우측의 주요 per-row 액션. 평소엔 상태(`✓ 준비됨`)를 보이고, hover/focus 시 그 자리를 `다시 선택`으로 swap한다. 전역 "파일 다시 선택" 버튼은 두지 않는다.
  - 마우스 hover와 키보드 `:focus-within` 모두에서 액션이 노출되어야 하며, 액션은 Tab 순서에 포함한다.
- **Readiness Progress** — 생성 전 입력 충족률만 표현한다. 트랙은 `{colors.border}`, 채움은 `{colors.progress}` 단색. 막대와 백분율·충족 개수를 항상 함께 표시한다. "설정 열기" 인라인 링크는 `{colors.accent}`.
- **Primary Button** — `영상 생성`·완료 확인. `{colors.primary-action}`(밝은) 배경과 `{colors.primary-action-foreground}`(어두운) 글자, `{rounded.full}`. 홈에서는 왼쪽 패널 최상단 줄의 **게시일 picker 오른쪽**에 둔다. **입력 준비 100%(필수 4/4) 전에는 비활성**, 준비 완료 시 활성화한다. (기존 청록 `#4a9` 폴백은 버그이며 제거한다.)
- **Secondary Button** — `파일 다시 선택`·`취소`·`교체`. `{colors.raised}` 배경, `{colors.border-strong}` 경계, `{colors.text-primary}` 글자, `{rounded.full}`.
- **Date Picker / Calendar Popover** — 닫힌 상태는 `YYYY-MM-DD · Sat` 트리거. 열린 팝오버는 `Sun`~`Sat` 영문 요일을 표시하고 오늘은 `{colors.border-strong}` 경계, 선택일만 `{colors.accent}` 채움 + `{colors.base}` 글자.
- **Completion Row** — 선행 아이콘 없이 밀도 높게 둬 한 화면에 더 많은 행이 보이게 한다(세로 패딩 `{spacing.2}` 수준). 게시일(`YYYY-MM-DD · Mon`)과 **스크립트 제목을 함께** 표시하고, 결과 폴더 상태와 폴더 열기 동작을 우측에 둔다. 선택 행은 `{colors.accent}` 좌측 바 + `{colors.selected}` 배경(아이콘 없음). 존재하지 않는 결과 폴더는 `{colors.warning}` 인라인 문구(`결과 폴더 없음`)로 표시한다.
- **Bottom Status Bar** — 두 요소만 둔다. 왼쪽은 `현재 작업: <제목>`(대기 점 `{colors.text-secondary}`, 실행 중 점 `{colors.progress}` 펄스) — JobSummary의 제목이 이곳으로 이동한다. 오른쪽은 **생성 진행률 바 하나**(`{colors.progress}` 채움)로, 폭을 완료 목록 열 폭에 맞춘다. 세로 구분선·"모든 기능은 로컬…" 같은 중복 텍스트는 두지 않는다. 생성 전 준비율은 이곳에 표시하지 않는다(그건 입력 준비 카드 소관).
- **Resource Settings Dialog** — 제목·말씀 영상, 기도 반복 영상, 기본 배경음악, 자막 폰트를 한 화면에 표시한다. 각 행은 **라벨 + 현재 파일명(또는 `미등록`) + 상태 + `교체`** 만 둔다. 행마다 반복되던 허용 포맷(MP4/MOV…) 상시 노출은 제거한다(필요 시 빈 상태·플레이스홀더에서만 안내). 상태색은 File Slot 규칙을 따른다. 시각 참고: [단순화 팝업](mockups/dialogs-simplified.html).
- **Guide Navigation / Guide Card** — 가이드 내부 섹션 탐색은 Sidebar Icon Button과 동일한 선택 표면(`{colors.accent}`)을 쓴다. 가이드 카드는 홈과 같은 표면·테두리 체계를 쓰고, `STEP 1` 같은 eyebrow 라벨은 `{colors.text-secondary}` 무채색으로 둔다.
- **Result Dialog (생성 완료)** — 단일 제목 줄(`✓ 영상이 완성되었습니다`, ✓는 `{colors.progress}`) + 스크립트 제목 + 게시일 한 줄만. **결과 경로(긴 문자열)·실제 생성일·이중 제목은 두지 않는다.** 동작은 `폴더 열기`(보조)와 `확인`(주요).
- **Failed Dialog (생성 실패)** — 단일 제목 + 단계 태그(`{colors.danger}`) + **다음 동작이 포함된 한 문장**(기술 details는 노출하지 않고 `로그 폴더` 뒤에 둔다). 버튼은 주요 복구(`입력 수정`)와 보조 `로그 폴더` 두 개로 제한한다.
- **Confirm Dialog (취소/다시 생성)** — 한 문장 + 버튼 2개로 이미 최소화돼 있으니 유지한다. 파괴적 확인은 danger 강조.

시각 참고: [Mono Focus 색·로고 시안](.working/). 이 문서와 시안이 충돌하면 이 문서가 우선한다.

## Do's and Don'ts

| Do | Don't |
|---|---|
| accent 인디고는 선택·현재 위치에만 쓴다. | 장식·라벨·아이콘에 인디고를 흩뿌린다. |
| progress 인디고는 준비·진행·성공·실행중에만 쓴다. | 선택색과 진행색을 같은 자리에서 구분 없이 섞는다. |
| 준비율과 생성 진행률을 위치·문구로 분리한다. | 하나의 막대로 입력 준비와 렌더링을 모두 표현한다. |
| 게시일은 `YYYY-MM-DD · Mon`으로 일관 표기한다. | `06.27`, `오늘`만 써서 폴더명-날짜 대응을 흐린다. |
| 주요·보조 버튼은 알약형(full), 행·카드는 12px. | 버튼을 네모 박스로 두거나 모든 모서리를 같은 값으로 둔다. |
| 경고=앰버, 실패=빨강 의미를 고정한다. | 실패 상태를 무채색·인디고로 흐린다. |
| 사용자가 취할 다음 동작을 오류 문구에 포함한다. | 기술 코드만 모달에 표시한다. |
| 설정 모달은 한 단계만 연다. | 설정 모달 위에 파일 교체 확인 모달을 중첩한다. |
| 색·간격·타이포는 토큰으로만 표현한다. | 하드코딩 hex·px·머티리얼 색 폴백을 다시 들인다. |
