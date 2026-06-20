export function shouldBlockNavigation(currentUrl: string, targetUrl: string): boolean {
  if (targetUrl === currentUrl) {
    return false
  }

  try {
    const current = new URL(currentUrl)
    const target = new URL(targetUrl)

    current.hash = ''
    target.hash = ''

    return current.href !== target.href
  } catch {
    return true
  }
}
