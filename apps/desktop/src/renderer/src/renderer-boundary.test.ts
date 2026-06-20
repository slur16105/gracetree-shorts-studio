import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = resolve(directory, name)
    if (statSync(path).isDirectory()) return sourceFiles(path)
    return /\.(ts|tsx)$/.test(name) && !name.includes('.test.') ? [path] : []
  })
}

describe('renderer privilege boundary', () => {
  it('does not import filesystem, SQLite, child processes, or Electron', () => {
    const root = resolve(process.cwd(), 'src/renderer/src')
    const source = sourceFiles(root)
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n')

    expect(source).not.toMatch(/from ['"](?:node:)?fs/)
    expect(source).not.toMatch(/from ['"](?:node:)?child_process/)
    expect(source).not.toMatch(/from ['"]electron['"]/)
    expect(source).not.toMatch(/sqlite/i)
  })
})
