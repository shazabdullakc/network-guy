const NAV_ITEMS = [
  { label: 'Hero',         id: 'hero' },
  { label: 'Architecture', id: 'architecture' },
  { label: 'Commands',     id: 'commands' },
  { label: 'Bonus',        id: 'bonus' },
  { label: 'Deliverables', id: 'deliverables' },
  { label: 'Demo',         id: 'demo' },
]

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

export default function Navbar() {
  return (
    <nav
      style={{
        position:       'fixed',
        top:            0,
        left:           0,
        right:          0,
        zIndex:         50,
        height:         '64px',
        display:        'flex',
        alignItems:     'center',
        justifyContent: 'space-between',
        padding:        '0 2rem',
        background:     'rgba(0, 8, 15, 0.88)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderBottom:   '1px solid rgba(0, 245, 255, 0.18)',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <div
          style={{
            width:        '8px',
            height:       '8px',
            borderRadius: '50%',
            background:   '#00f5ff',
            boxShadow:    '0 0 12px #00f5ff',
            animation:    'pulse-glow 2s ease-in-out infinite',
          }}
        />
        <span
          style={{
            fontFamily:    'var(--font-heading)',
            color:         'var(--cyan)',
            textShadow:    '0 0 20px rgba(0, 245, 255, 0.6)',
            fontSize:      '1.1rem',
            fontWeight:    700,
            letterSpacing: '0.06em',
            userSelect:    'none',
          }}
        >
          NetFix AI
        </span>
      </div>

      {/* Nav Links */}
      <div className="nav-links" style={{ display: 'flex', gap: '0.15rem', alignItems: 'center' }}>
        {NAV_ITEMS.map(({ label, id }) => (
          <button
            key={id}
            onClick={() => scrollTo(id)}
            style={{
              background:   'none',
              border:       'none',
              cursor:       'pointer',
              fontFamily:   'var(--font-mono)',
              fontSize:     '0.78rem',
              color:        'var(--text-muted)',
              padding:      '0.5rem 0.8rem',
              borderRadius: '6px',
              transition:   'color 0.2s, background 0.2s',
              letterSpacing: '0.04em',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.color      = 'var(--cyan)'
              e.currentTarget.style.background = 'rgba(0,245,255,0.07)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.color      = 'var(--text-muted)'
              e.currentTarget.style.background = 'none'
            }}
          >
            {label}
          </button>
        ))}

        {/* GitHub button */}
        <a
          href="https://github.com/shazabdullakc/network-guy"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display:      'inline-flex',
            alignItems:   'center',
            gap:          '0.4rem',
            marginLeft:   '0.5rem',
            padding:      '0.45rem 0.9rem',
            borderRadius: '6px',
            border:       '1px solid rgba(0,245,255,0.35)',
            background:   'rgba(0,245,255,0.06)',
            color:        'var(--cyan)',
            fontFamily:   'var(--font-heading)',
            fontSize:     '0.7rem',
            letterSpacing: '0.05em',
            textDecoration: 'none',
            transition:   'background 0.2s, box-shadow 0.2s, border-color 0.2s',
            whiteSpace:   'nowrap',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background   = 'rgba(0,245,255,0.14)'
            e.currentTarget.style.boxShadow    = '0 0 20px rgba(0,245,255,0.3)'
            e.currentTarget.style.borderColor  = 'rgba(0,245,255,0.6)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background   = 'rgba(0,245,255,0.06)'
            e.currentTarget.style.boxShadow    = 'none'
            e.currentTarget.style.borderColor  = 'rgba(0,245,255,0.35)'
          }}
        >
          {/* GitHub SVG icon */}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
            <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
          </svg>
          GitHub
        </a>
      </div>

      <style>{`
        @media (max-width: 700px) { .nav-links { display: none !important; } }
      `}</style>
    </nav>
  )
}
