# 릴리스 게이트 정책 — Story 2.11

> 이 문서는 품질 검사 결과가 릴리스를 어떻게 차단하는지 명시한다.
> 참조: `rubric.yaml`, `check_quality.py`, `RELEASE_QUALITY_REPORT.md`

---

## 1. 게이트 종류

| 게이트 ID | 이름 | 차단 조건 | 해제 조건 |
|-----------|------|-----------|-----------|
| **GATE-AUTO** | 자동 Regression 게이트 | 자동 검사 결정적(critical) 항목 실패 1건 이상 | 모든 critical 자동 항목 100% PASS |
| **GATE-QUALITY** | 품질 표본 게이트 | 10개 fixture 중 게시 가능 < 8개 | 10개 중 8개 이상 PUBLISHABLE |

---

## 2. 차단 범위

### GATE-AUTO — 자동 Regression 게이트

**차단 대상 릴리스 활동:**
- Engine 코드 변경 후 빌드 및 QA 진행
- 스테이징(Staging) 환경 배포
- 프로덕션(Production) 릴리스

**트리거 조건:**
```
check_quality.py 실행 결과 중 다음 중 하나라도 FAIL:
  - auto-dimensions   (1080×1920 미충족)
  - auto-fps          (30fps ±0.5 초과)
  - auto-streams      (비디오 또는 오디오 스트림 없음)
  - auto-duration     (1초 미만)
  - auto-subtitles-exist  (subtitles.ass 없거나 빔)
  - auto-timing-valid     (timing.json 유효하지 않은 JSON)
```

**중요:** `critical: true` 항목 실패는 해당 fixture가 **즉시 NOT PUBLISHABLE**로 판정된다.
비결정적(critical: false) 항목(`auto-black-frames`, `auto-audio-loudness`) 실패는 GATE-QUALITY 집계에만 반영된다.

**해제 절차:**
1. `check_quality.py` 재실행 → 모든 critical 항목 PASS 확인
2. `RELEASE_QUALITY_REPORT.md`의 자동 검사 요약 테이블 업데이트
3. 담당자 서명 후 릴리스 재승인

---

### GATE-QUALITY — 품질 표본 게이트

**차단 대상 릴리스 활동:**
- 프로덕션(Production) 릴리스 (최초 공개 또는 주요 Engine 업데이트)

> GATE-AUTO가 차단하는 경우 GATE-QUALITY 평가는 진행하지 않는다.
> (자동 Regression 게이트가 먼저 해제되어야 품질 표본 평가에 의미가 있다.)

**트리거 조건:**
```
다음 조건 중 하나 이상 충족 시 GATE-QUALITY 실패:
  1. 자동 검사(critical 포함 전체) + 수동 평가 결과 fixture별 PUBLISHABLE 집계 시 합산 < 8개 / 10개
  2. 10개 중 평가 완료 fixture가 10개 미만인 경우 (미평가는 FAIL로 집계)
```

**평가 방법:**
- Fixture별 PUBLISHABLE 여부는 `check_quality.py`의 자동 검사 결과 + `manual_evaluation_form.md`의 수동 평가 최종 결론을 AND 조건으로 결합한다.
  - 자동 PASS + 수동 PUBLISHABLE → 해당 fixture **PUBLISHABLE**
  - 자동 PASS + 수동 NOT PUBLISHABLE → 해당 fixture **NOT PUBLISHABLE**
  - 자동 FAIL (critical) → 수동 평가 없이 즉시 **NOT PUBLISHABLE**

**해제 절차:**
1. NOT PUBLISHABLE fixture에 대해 보정 또는 재생성
2. 보정 후 해당 fixture만 재평가 (자동 + 수동)
3. 8/10 이상 PUBLISHABLE 확인 후 `RELEASE_QUALITY_REPORT.md`에 최종 결과 기록
4. 담당자 서명 후 프로덕션 릴리스 승인

---

## 3. 게이트 의사결정 흐름

```
check_quality.py 실행
        │
        ▼
critical 항목 실패 있음?
   YES ──► GATE-AUTO 차단 → 릴리스 전면 차단
   NO  ──► GATE-AUTO 통과 ────────────────────────┐
                                                  ▼
                                      수동 평가 진행 (manual_evaluation_form.md)
                                                  │
                                                  ▼
                                      PUBLISHABLE fixture 합산 >= 8 / 10 ?
                                         YES ──► GATE-QUALITY 통과 → 릴리스 승인
                                         NO  ──► GATE-QUALITY 차단 → 보정 후 재평가
```

---

## 4. 역할과 책임

| 역할 | 책임 |
|------|------|
| 개발자 (Dev) | `check_quality.py` 실행 및 자동 검사 결과 확인 |
| QA / 평가자 | `manual_evaluation_form.md` 작성 및 수동 평가 완료 |
| 릴리스 담당자 | `RELEASE_QUALITY_REPORT.md` 최종 서명 및 릴리스 승인 |

---

## 5. 정책 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2026-06-25 | 1.0 | 초안 작성 (Story 2.11) | Dev Agent |
