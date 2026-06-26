const STAGE_LABELS: Record<string, string> = {
  speech_alignment: '음성 정렬',
  vertical_slice: '수직 슬라이스 진단',
}

const ERROR_MESSAGES: Record<string, string> = {
  PRAYER_BOUNDARY_AMBIGUOUS: '기도 시작 위치를 찾을 수 없습니다.',
  PROCESS_FAILED: '처리 중 오류가 발생했습니다.',
}

export function stageLabel(stageId: string | null): string {
  return stageId ? (STAGE_LABELS[stageId] ?? stageId) : '초기화'
}

export function errorMessage(errorCode: string): string {
  return ERROR_MESSAGES[errorCode] ?? '알 수 없는 오류가 발생했습니다.'
}
