# Acceptance Auditor Review Prompt

다음 파일을 모두 읽어라.

- `AGENTS.md`
- `_bmad-output/implementation-artifacts/spec-agents-md-karpathy-guidelines.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`

검토 목표:

1. 사양의 모든 Acceptance Criteria와 완료된 task가 실제 `AGENTS.md`에 반영됐는지 확인한다.
2. `<frozen-after-approval>`의 Always, Ask First, Never 규칙 누락 또는 의미 변경을 찾는다.
3. Architecture·Epics와 충돌하는 규칙을 찾는다.
4. 기존 작업 트리 변경을 보존하고 `AGENTS.md`만 제품 산출물로 추가했다는 범위가 지켜졌는지 `git diff`와 `git status`로 확인한다.
5. 문서가 작업 행동 계약으로 충분히 짧고 구체적이며, 상세 아키텍처를 불필요하게 복제하지 않는지 확인한다.

각 발견은 다음 형식으로 작성하라.

- 분류: acceptance / scope / conflict / verification
- 심각도
- 근거
- 실패 영향
- 최소 수정안

모든 기준을 충족하면 `No findings`와 확인한 기준 목록을 답하라.
