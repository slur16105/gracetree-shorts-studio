---
name: GraceTree Studio Black
description: 말씀기도 쇼츠 제작 상태와 결과를 빠르게 읽는 다크 데스크톱 제작 도구.
status: final
created: 2026-06-19
updated: 2026-06-19
sources:
  - ../../prds/prd-gracetree-shorts-studio-2026-06-19/prd.md
  - ../../prds/prd-gracetree-shorts-studio-2026-06-19/addendum.md
  - ../../../../docs/idea.md
colors:
  surface-base: '#080909'
  surface-nav: '#090A0A'
  surface-panel: '#0D0F0F'
  surface-raised: '#171919'
  surface-hover: '#202424'
  surface-selected: '#242727'
  text-primary: '#F4F5F5'
  text-secondary: '#9FA4A4'
  text-disabled: '#666B6B'
  border-subtle: '#292D2D'
  border-strong: '#686E6E'
  brand-accent: '#FF2F62'
  brand-accent-foreground: '#080909'
  success: '#36D399'
  success-muted: '#17201D'
  warning: '#F2B84B'
  danger: '#F05D5E'
  primary-action: '#F4F5F5'
  primary-action-foreground: '#080909'
  focus-ring: '#7DD3FC'
typography:
  title-lg:
    fontFamily: 'Inter, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.25'
    letterSpacing: -0.02em
  title-md:
    fontFamily: 'Inter, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 20px
    fontWeight: '700'
    lineHeight: '1.35'
    letterSpacing: -0.01em
  body:
    fontFamily: 'Inter, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.55'
  label:
    fontFamily: 'Inter, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 13px
    fontWeight: '600'
    lineHeight: '1.4'
  meta:
    fontFamily: 'Inter, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
  eyebrow:
    fontFamily: 'Inter, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
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
  rail-width: 78px
  bottom-status-height: 70px
components:
  sidebar-icon-button:
    size: 44px
    radius: '{rounded.md}'
    foreground: '{colors.text-secondary}'
    active-background: '{colors.surface-selected}'
    active-foreground: '{colors.text-primary}'
  drop-zone:
    background: '{colors.surface-panel}'
    border: '{colors.border-strong}'
    radius: '{rounded.lg}'
  primary-button:
    background: '{colors.primary-action}'
    foreground: '{colors.primary-action-foreground}'
    radius: '{rounded.full}'
  secondary-button:
    background: '{colors.surface-raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border-strong}'
    radius: '{rounded.full}'
  readiness-progress:
    track: '{colors.surface-selected}'
    fill: '{colors.success}'
    height: 5px
  render-progress:
    track: '{colors.surface-selected}'
    fill: '{colors.success}'
    height: 4px
  completion-row:
    background: transparent
    selected-background: '{colors.surface-hover}'
    selected-border: '{colors.border-strong}'
    radius: '{rounded.md}'
  calendar-popover:
    background: '{colors.surface-raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border-strong}'
    selected-background: '{colors.brand-accent}'
    selected-foreground: '{colors.brand-accent-foreground}'
    radius: '{rounded.md}'
  resource-settings-dialog:
    background: '{colors.surface-raised}'
    foreground: '{colors.text-primary}'
    border: '{colors.border-strong}'
    radius: '{rounded.lg}'
  guide-card:
    background: '{colors.surface-raised}'
    border: '{colors.border-subtle}'
    radius: '{rounded.md}'
---

## Brand & Style

GraceTree Studio Black은 영상 편집기가 아니라 반복 제작을 확실하게 끝내는 로컬 작업 도구다. YouTube Music 데스크톱의 익숙한 공간 구조를 참고하되, 재생 중심 메타포를 그대로 복제하지 않고 `입력 → 준비 확인 → 생성 → 결과 확인`의 흐름으로 치환한다.

화면은 검은색과 짙은 회색의 층으로 구성한다. 사용자의 파일명, 스크립트 제목, 게시 날짜와 생성 상태가 시각 장식보다 우선한다. 분홍색은 브랜드·선택 지점에만 사용하고, 녹색은 준비·성공·진행이라는 운영 상태에만 사용한다. 제품의 정서는 차분하지만 종교적 장식을 전면에 내세우지 않는다.

## Colors

- `{colors.surface-base}`는 앱의 최하단 캔버스다.
- `{colors.surface-panel}`과 `{colors.surface-raised}`는 드롭 영역, 완료 목록 선택 행, 팝오버와 모달을 단계적으로 분리한다.
- `{colors.text-primary}`는 제목과 주요 동작, `{colors.text-secondary}`는 파일 설명·날짜·보조 상태에 사용한다.
- `{colors.brand-accent}`는 앱 로고, 달력 선택일, 현재 탐색 지점처럼 사용자가 직접 선택한 위치에만 쓴다. 작은 선택일 텍스트는 `{colors.brand-accent-foreground}`를 사용해 4.5:1 이상의 대비를 유지한다.
- `{colors.success}`는 입력 준비율, 생성 진행률, 리소스 정상 상태와 생성 성공에만 쓴다.
- `{colors.warning}`은 확인이 필요한 입력과 중단 가능 상태, `{colors.danger}`는 실패와 파괴적 확인에만 쓴다.
- 주요 본문 조합은 WCAG 2.2 AA의 일반 텍스트 대비 4.5:1 이상을 목표로 한다. 비활성 텍스트는 정보를 전달하는 유일한 수단으로 사용하지 않는다.

## Typography

Windows와 macOS 모두에서 동일한 밀도를 유지하도록 Inter 또는 Pretendard를 우선하고, 설치되지 않은 환경에서는 플랫폼 시스템 산세리프로 대체한다.

- 작업 제목과 화면 제목은 `{typography.title-md}` 또는 `{typography.title-lg}`.
- 파일명과 버튼은 `{typography.label}`.
- 설명과 오류 해결 문장은 `{typography.body}`.
- 게시일, 실제 생성일, 진행률 보조 정보는 `{typography.meta}`.
- 영문 대문자 안내는 화면당 하나 이하로 제한하고 `{typography.eyebrow}`를 사용한다.

작업 제목은 `script.txt`의 `[제목]` 줄바꿈을 공백으로 합쳐 한 줄로 표시한다. 완료 목록에서는 말줄임표를 허용하지만 전체 제목은 툴팁 또는 접근성 이름으로 제공한다.

## Layout & Spacing

기본 창은 데스크톱 가로형이며 권장 최소 콘텐츠 크기는 1180×720이다.

- 전역 사이드바: `{spacing.rail-width}`.
- 홈 본문: 왼쪽 작업 영역 약 42%, 오른쪽 완료 목록 나머지 영역.
- 하단 상태 바: `{spacing.bottom-status-height}`로 고정.
- 주요 컨테이너 내부 여백은 `{spacing.6}`~`{spacing.7}`, 행 내부는 `{spacing.3}`~`{spacing.4}`.
- 버튼 묶음은 보조 동작을 왼쪽, 주요 생성 동작을 오른쪽에 둔다.
- 창이 좁아져도 완료 목록은 사라지지 않으며, 최소 창 폭에서는 좌우 패널의 최소 폭을 유지한다. 모바일 레이아웃은 제공하지 않는다.

## Elevation & Depth

기본 화면은 그림자보다 표면 색과 1px 경계로 깊이를 만든다. 달력 팝오버와 설정 모달만 배경 위에 뜨는 요소이므로 넓고 낮은 불투명도의 그림자를 허용한다. 중첩 모달은 금지한다.

## Shapes

도구형 화면의 선명함을 유지하면서 딱딱하지 않도록 8/12/18/20px 반경을 사용한다. 버튼은 주요·보조 동작에 한해 `{rounded.full}`을 사용한다. 목록 행과 파일 슬롯은 `{rounded.md}`, 큰 드롭 영역과 모달은 `{rounded.lg}`를 사용한다.

## Components

- **Sidebar Icon Button** — 44×44px. 홈, 사용 가이드, 공통 리소스 설정을 제공한다. 활성 항목은 `{colors.surface-selected}` 배경과 `{colors.text-primary}` 아이콘을 사용한다.
- **Drop Zone** — 큰 점선 경계와 중앙 안내를 가진다. 드래그 진입 시 경계를 `{colors.focus-ring}`으로 바꾸고 표면을 한 단계 밝힌다. 등록 후에는 파일 슬롯을 내부에 표시한다.
- **File Slot** — 역할, 파일명, 정상·충돌·누락 상태를 한 행에 표시한다. 정상은 `{colors.success}`, 확인 필요는 `{colors.warning}`, 오류는 `{colors.danger}`를 사용하되 아이콘과 문구를 함께 제공한다.
- **Date Picker** — 닫힌 상태는 `YYYY-MM-DD · Sat`. 열린 **Calendar Popover**는 `Sun`부터 `Sat`까지 영문 요일을 표시하고 선택일만 `{colors.brand-accent}`로 채운다.
- **Job Summary** — 스크립트 제목, 제목 출처 또는 오류, 준비 상태를 표시한다. 오른쪽 상태 블록에 `준비 완료`와 `100% · 필수 입력 4/4`를 세로로 배치한다.
- **Readiness Progress** — 생성 전 입력 충족률만 표현한다. 막대와 백분율·충족 개수를 항상 함께 표시한다.
- **Primary Button** — `영상 생성` 또는 완료 확인. 밝은 배경과 어두운 글자. 버튼 묶음의 오른쪽에 둔다.
- **Secondary Button** — `파일 다시 선택`, `취소`, `교체`. 짙은 배경, 밝은 글자와 명확한 경계.
- **Completion Row** — 제목, `YYYY-MM-DD · Mon`, 실제 생성일, 결과 폴더 상태, 폴더 열기 동작을 표시한다. 존재하지 않는 결과 폴더는 경고 아이콘과 문구를 사용한다.
- **Bottom Status Bar** — 최근 작업 요약과 현재 생성 단계·진행률을 표시한다. 생성 전 준비율은 이곳에 표시하지 않는다.
- **Resource Settings Dialog** — 제목·말씀 영상, 기도 반복 영상, 기본 배경음악, 자막 폰트를 한 화면에 표시한다. 각 행은 현재 파일명, 유효 상태, `교체` 동작을 갖는다.
- **Guide Navigation** — 가이드 화면의 내부 섹션 탐색이다. 활성 항목은 Sidebar Icon Button과 동일한 선택 표면을 사용한다.
- **Guide Card** — 가이드 화면의 3단계 시작 안내와 파일 규칙을 표현한다. 홈 화면과 같은 표면·테두리 체계를 사용한다.
- **Result Dialog** — 완료·실패·취소 확인에 사용한다. 제목, 한 문장 요약, 다음 동작을 제공하며 상세 기술 로그는 직접 노출하지 않는다.

시각 참고: [Studio Black 홈·달력·설정·가이드](mockups/studio-black-reference.html#direction-a). 이 문서와 참고 시안이 충돌하면 이 문서가 우선한다.

## Do's and Don'ts

| Do | Don't |
|---|---|
| 준비율과 생성 진행률을 위치·문구로 분리한다. | 하나의 막대로 입력 준비와 렌더링을 모두 표현한다. |
| 게시일은 `YYYY-MM-DD · Mon`으로 일관되게 표시한다. | `06.19`, `오늘`만 사용해 폴더명과 날짜 대응을 흐린다. |
| 분홍색은 선택, 녹색은 정상·진행 의미로 고정한다. | 동일한 색을 장식과 오류에 섞어 쓴다. |
| 사용자가 취할 다음 동작을 오류 문구에 포함한다. | 기술 코드만 모달에 표시한다. |
| 설정 모달은 한 단계만 연다. | 설정 모달 위에 파일 교체 확인 모달을 중첩한다. |
| 완료 목록은 홈 오른쪽에 유지한다. | 중복된 완료 목록 전용 사이드바 화면을 만든다. |
