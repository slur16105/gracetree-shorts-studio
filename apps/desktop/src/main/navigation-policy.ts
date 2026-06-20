export function shouldBlockNavigation(currentUrl: string, targetUrl: string): boolean {
  return targetUrl !== currentUrl
}
