interface SidebarIconProps {
  name: 'home' | 'guide' | 'settings'
}

export function SidebarIcon({ name }: SidebarIconProps): React.JSX.Element {
  if (name === 'home') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M4 10.5 12 4l8 6.5V20h-5v-6H9v6H4z" />
      </svg>
    )
  }

  if (name === 'guide') {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M5 4h10a4 4 0 0 1 4 4v12H8a3 3 0 0 1-3-3zm3 12h8V8a1 1 0 0 0-1-1H8z" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7m8 3.5-.1-1.2 2-1.5-2-3.4-2.4 1a8 8 0 0 0-2-1.2L15.2 3h-4l-.4 2.7a8 8 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.5L6.3 12l.1 1.2-2 1.5 2 3.4 2.4-1a8 8 0 0 0 2 1.2l.4 2.7h4l.4-2.7a8 8 0 0 0 2-1.2l2.4 1 2-3.4-2-1.5z" />
    </svg>
  )
}
