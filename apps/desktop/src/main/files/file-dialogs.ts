import type { SelectedInputFile } from '@gracetree/contracts/desktop-api'
import { dialog } from 'electron'
import { basename } from 'node:path'

export async function selectInputFiles(): Promise<SelectedInputFile[]> {
  const result = await dialog.showOpenDialog({
    properties: ['openFile', 'multiSelections'],
    title: '입력 파일 선택'
  })
  if (result.canceled) return []
  return result.filePaths.map((sourcePath) => ({
    name: basename(sourcePath),
    sourcePath
  }))
}
