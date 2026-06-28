interface SidebarIconProps {
  name: 'home' | 'guide' | 'settings'
}

// Monoline (stroke) icons to match the Mono Focus sprout mark.
export function SidebarIcon({ name }: SidebarIconProps): React.JSX.Element {
  const common = {
    'aria-hidden': true,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const
  }

  if (name === 'home') {
    return (
      <svg {...common}>
        <path d="M3 9.5 12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" />
      </svg>
    )
  }

  if (name === 'guide') {
    return (
      <svg {...common}>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    )
  }

  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5l1.6 2.2a7.4 7.4 0 0 1 2 .85l2.6-.7 1.7 3-2 1.8a7.5 7.5 0 0 1 0 2.1l2 1.8-1.7 3-2.6-.7a7.4 7.4 0 0 1-2 .85L12 21.5l-1.6-2.2a7.4 7.4 0 0 1-2-.85l-2.6.7-1.7-3 2-1.8a7.5 7.5 0 0 1 0-2.1l-2-1.8 1.7-3 2.6.7a7.4 7.4 0 0 1 2-.85z" />
    </svg>
  )
}
