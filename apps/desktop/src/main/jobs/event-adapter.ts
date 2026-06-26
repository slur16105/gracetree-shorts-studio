import type { AppError } from '@gracetree/contracts/desktop-api'

const ERROR_MESSAGES: Record<string, string> = {
  PRAYER_BOUNDARY_AMBIGUOUS: '기도 시작 위치를 찾을 수 없습니다.',
  PROCESS_FAILED: '처리 중 오류가 발생했습니다.',
}

export function mapToAppError(
  errorCode: string,
  stageId: string | null,
  recoverable: boolean,
  details: string | null
): AppError {
  return {
    code: errorCode,
    message: ERROR_MESSAGES[errorCode] ?? '알 수 없는 오류가 발생했습니다.',
    recoverable,
    details,
  }
}
