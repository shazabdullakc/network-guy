const NAV_ITEMS = [
  { label: 'Hero',         id: 'hero' },
  { label: 'Architecture', id: 'architecture' },
  { label: 'Commands',     id: 'commands' },
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
      <div className="nav-links" style={{ display: 'flex', gap: '0.25rem' }}>
        {NAV_ITEMS.map(({ label, id }) => (
          <button
            key={id}
            onClick={() => scrollTo(id)}
            style={{
              background:   'none',
              border:       'none',
              cursor:       'pointer',
              fontFamily:   'var(--font-mono)',
              fontSize:     '0.82rem',
              color:        'var(--text-muted)',
              padding:      '0.5rem 1rem',
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
      </div>

      <style>{`
        @media (max-width: 600px) { .nav-links { display: none !important; } }
      `}</style>
    </nav>
  )
}
