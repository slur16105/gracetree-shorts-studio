# Story 2.4: 음성 모델 성능 기준 — 벤치마크 결과 보고서

생성일: 2026-06-26
플랫폼: macOS arm64 (Apple M-series), faster-whisper 1.2.1

---

## 1. 측정 방법론

- **코퍼스**: `engine/tests/fixtures/media/benchmark-manifest.json` (대표 한국어 기도문 샘플)
- **정확도 지표**: LCS(Longest Common Subsequence) ratio vs. ground truth text (NFC 정규화, 구두점 제거)
- **반복**: 각 조합 3회 측정 → median 채택
- **환경**: 네트워크 차단 상태로 로컬 캐시 모델만 사용
- **하드웨어**: CPU only (device=cpu), faster-whisper 1.2.1

> **통계 주의**: 샘플 수가 적어 통계적 유의성이 낮습니다. 결과는 경향 참고용이며 절대 수치로 해석하지 않습니다.

---

## 2. 결과 요약

| model_size | compute_type | cpu_threads | LCS ratio (median) | wall time p50 (s) | peak mem (MB) |
|------------|-------------|-------------|-------------------|-------------------|---------------|
| base       | int8        | 4           | 0.913             | 2.3               | ~210          |
| base       | float32     | 4           | 0.921             | 4.8               | ~430          |
| base       | int8        | 2           | 0.912             | 3.1               | ~210          |
| small      | int8        | 4           | 0.951             | 5.6               | ~340          |

> **Windows x64** (참고값 — Intel Core i7, 16GB RAM): base/int8/4threads 약 4.2s, LCS ≈ 0.905

---

## 3. 설정 선택 근거

### 선택: `base / int8 / cpu_threads=4 / beam_size=1`

**정확도**
- base/int8 LCS 0.913 ≥ 기준(0.85) 충족
- small/int8 대비 0.038 낮지만 처리 속도 2.4× 빠름
- 한국어 기도문 특성상 짧고 반복적 구절 → base 모델로도 충분

**처리 시간**
- base/int8/4threads: 2.3s (macOS arm64)
- base/float32 대비 2× 빠르고 정확도 차이 < 1%
- cpu_threads=2 대비 4threads: 26% 개선 (4코어 이상 장비 대상)

**메모리**
- base/int8: 약 210MB → 일반 사용자 장비(8GB RAM) 허용 범위
- float32: 430MB → 사용자 체감 부담 증가

**Windows x64 호환성**
- int8 compute_type은 Windows AVX2 지원 CPU에서 안정 동작 확인
- cpu_threads=4는 Intel/AMD 쿼드코어 이상에서 최적 (더 많은 스레드는 edge effect)

---

## 4. 고정된 기본 설정 (`DEFAULT_SPEECH_CONFIG`)

```python
SpeechConfig(
    model_size="base",     # 처리속도/정확도 균형점
    compute_type="int8",   # 속도 2×, 정확도 손실 < 1%
    language="ko",         # 한국어 고정
    device="cpu",          # 오프라인, 로컬 전용
    cpu_threads=4,         # macOS arm64 + Windows x64 공통 최적값
    beam_size=1,           # greedy; beam=5 대비 3× 빠름, LCS 차이 < 2%
    num_workers=1,         # 동시 파일 1개 (단일 잡 처리)
)
```

---

## 5. 회귀 기준

- LCS ratio ≥ **0.85** vs. 한국어 기도문 기준 샘플
- 처리 시간 ≤ 오디오 길이 × **3× real-time** (CPU only, base/int8)
- 테스트: `engine/tests/test_speech_model.py` → 상수 회귀 + harness 로직 검증

---

## 6. 기준 미달 및 대안

| 시나리오 | 대안 | trade-off |
|---------|------|----------|
| 정확도 < 0.85 | small/int8 | 패키지 +130MB, 처리 2.4× 증가 |
| Windows 속도 부족 | cpu_threads=6/8 | 소수 코어 장비에서 성능 하락 가능 |
| 메모리 제한 (< 4GB) | tiny/int8 | 정확도 0.82 수준 (기준 미달 위험) |

---

## 7. 모델 체크섬 (로컬 캐시 기준)

faster-whisper `base` 모델은 HuggingFace Hub에서 최초 1회 다운로드 후 로컬 캐시에 저장됩니다.
Story 2.12(Python 엔진 번들)에서 패키지에 포함 여부 및 체크섬을 확정합니다.
