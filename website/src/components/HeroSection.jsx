import { useEffect, useState } from 'react'
import GlobeCanvas from '../canvas/GlobeCanvas'

const HEADLINE_WORDS = [
  'We', "Didn't", 'Build', 'a', 'Chatbot.', 'We', 'Built', 'an', 'AI', 'Network', 'Engineer.'
]

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

// Animated typing badge
function TypedBadge() {
  const TEXTS = ['Attack-Aware.', 'Evidence-Backed.', 'Always Cited.', '<60 Seconds.']
  const [idx, setIdx] = useState(0)
  const [displayed, setDisplayed] = useState('')
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const target = TEXTS[idx]
    if (!deleting && displayed.length < target.length) {
      const id = setTimeout(() => setDisplayed(target.slice(0, displayed.length + 1)), 60)
      return () => clearTimeout(id)
    }
    if (!deleting && displayed.length === target.length) {
      const id = setTimeout(() => setDeleting(true), 1800)
      return () => clearTimeout(id)
    }
    if (deleting && displayed.length > 0) {
      const id = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 35)
      return () => clearTimeout(id)
    }
    if (deleting && displayed.length === 0) {
      setDeleting(false)
      setIdx(i => (i + 1) % TEXTS.length)
    }
  }, [displayed, deleting, idx])

  return (
    <span style={{ color: 'var(--cyan)', fontFamily: 'var(--font-mono)', fontSize: '0.95rem' }}>
      {displayed}
      <span style={{ animation: 'blink 0.8s step-start infinite', color: 'var(--cyan)' }}>|</span>
    </span>
  )
}

export default function HeroSection() {
  const [wordVisible, setWordVisible] = useState(Array(HEADLINE_WORDS.length).fill(false))
  const [subVisible,  setSubVisible]  = useState(false)
  const [btnVisible,  setBtnVisible]  = useState(false)
  const [statsVis,    setStatsVis]    = useState(false)

  useEffect(() => {
    const ids = []
    HEADLINE_WORDS.forEach((_, i) => {
      ids.push(setTimeout(() => {
        setWordVisible(prev => {
          const next = [...prev]; next[i] = true; return next
        })
      }, 300 + i * 90))
    })
    const afterWords = 300 + HEADLINE_WORDS.length * 90
    ids.push(setTimeout(() => setSubVisible(true),  afterWords + 80))
    ids.push(setTimeout(() => setBtnVisible(true),  afterWords + 260))
    ids.push(setTimeout(() => setStatsVis(true),    afterWords + 440))
    return () => ids.forEach(id => clearTimeout(id))
  }, [])

  // Mini stat counters in hero
  const MINI_STATS = [
    { value: '18', label: 'Benchmark Queries', suffix: '' },
    { value: '7',  label: 'Attack Types Detected', suffix: '' },
    { value: '5',  label: 'Specialized Agents', suffix: '' },
    { value: '<60',label: 'Seconds to RCA', suffix: 's' },
  ]

  return (
    <section
      id="hero"
      style={{
        position:    'relative',
        minHeight:   '100vh',
        display:     'flex',
        flexDirection: 'column',
        alignItems:  'center',
        justifyContent: 'center',
        paddingTop:  '64px',
        overflow:    'hidden',
        zIndex:      1,
      }}
    >
      {/* Globe — fills the FULL hero so scattered nodes don't clip */}
      <div
        className="hero-globe-wrap"
        style={{
          position:      'absolute',
          inset:         0,
          pointerEvents: 'auto',
          zIndex:        0,
          overflow:      'visible',
        }}
      >
        {/* Canvas fills the whole hero; globe centers itself via W/2,H/2 projection */}
        <div style={{ width: '100%', height: '100%', opacity: 0.92 }}>
          <GlobeCanvas />
        </div>
      </div>

      {/* Text content — centered over globe, pointer-events none so cursor reaches canvas */}
      <div
        style={{
          position:      'relative',
          zIndex:        2,
          textAlign:     'center',
          padding:       '0 1.5rem',
          maxWidth:      '800px',
          // Text containers are non-interactive so cursor passes through to globe
          pointerEvents: 'none',
        }}
      >
        {/* GitHub pill — above headline */}
        <a
          href="https://github.com/shazabdullakc/network-guy"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display:       'inline-flex',
            alignItems:    'center',
            gap:           '0.5rem',
            padding:       '0.45rem 1.1rem',
            borderRadius:  '99px',
            border:        '1px solid rgba(0,245,255,0.3)',
            background:    'rgba(0,245,255,0.06)',
            color:         'var(--cyan)',
            fontFamily:    'var(--font-mono)',
            fontSize:      '0.72rem',
            letterSpacing: '0.04em',
            textDecoration:'none',
            marginBottom:  '1.5rem',
            pointerEvents: 'auto',
            transition:    'background 0.2s, box-shadow 0.2s',
            opacity:       wordVisible[0] ? 1 : 0,
            transform:     wordVisible[0] ? 'none' : 'translateY(-12px)',
            transitionProperty: 'opacity, transform, background, box-shadow',
            transitionDuration: '0.5s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(0,245,255,0.12)'
            e.currentTarget.style.boxShadow  = '0 0 20px rgba(0,245,255,0.25)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'rgba(0,245,255,0.06)'
            e.currentTarget.style.boxShadow  = 'none'
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
          </svg>
          View on GitHub
          <span style={{ opacity: 0.5 }}>→</span>
        </a>

        {/* Headline */}
        <h1
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(2rem, 5vw, 3.4rem)',
            lineHeight:   1.2,
            color:        'var(--text)',
            marginBottom: '1rem',
            textShadow:   '0 2px 40px rgba(0,0,0,0.8)',
          }}
        >
          {HEADLINE_WORDS.map((word, i) => (
            <span
              key={i}
              style={{
                display:    'inline-block',
                marginRight: word === 'Chatbot.' ? '0.55em' : '0.28em',
                opacity:    wordVisible[i] ? 1 : 0,
                transform:  wordVisible[i] ? 'translateY(0)' : 'translateY(28px)',
                transition: 'opacity 0.55s ease, transform 0.55s ease',
                // Highlight "AI Network Engineer." words in cyan
                color:      ['AI', 'Network', 'Engineer.'].includes(word)
                  ? 'var(--cyan)'
                  : 'var(--text)',
                textShadow: ['AI', 'Network', 'Engineer.'].includes(word)
                  ? '0 0 30px rgba(0,245,255,0.4)'
                  : '0 2px 40px rgba(0,0,0,0.8)',
              }}
            >
              {word}
            </span>
          ))}
        </h1>

        {/* Typed subtext */}
        <div
          style={{
            opacity:    subVisible ? 1 : 0,
            transform:  subVisible ? 'none' : 'translateY(16px)',
            transition: 'opacity 0.55s ease, transform 0.55s ease',
            marginBottom: '2rem',
            minHeight:  '1.6rem',
          }}
        >
          <TypedBadge />
        </div>

        {/* Static tagline */}
        <p
          style={{
            color:      'var(--text-muted)',
            fontSize:   '0.95rem',
            lineHeight: 1.7,
            marginBottom: '2.5rem',
            opacity:    subVisible ? 1 : 0,
            transition: 'opacity 0.55s ease 0.15s',
            textShadow: '0 1px 20px rgba(0,0,0,0.9)',
          }}
        >
          Root cause analysis in under 60 seconds.
          Evidence-backed. Attack-aware. Always cited.
        </p>

        {/* CTA Buttons — re-enable pointer events so they're clickable */}
        <div
          style={{
            display:        'flex',
            gap:            '1rem',
            flexWrap:       'wrap',
            justifyContent: 'center',
            opacity:    btnVisible ? 1 : 0,
            transform:  btnVisible ? 'none' : 'translateY(16px)',
            transition: 'opacity 0.55s ease, transform 0.55s ease',
            pointerEvents: 'auto',
          }}
        >
          <button
            onClick={() => scrollTo('architecture')}
            style={{
              background:   'var(--cyan)',
              color:        '#00080f',
              border:       'none',
              padding:      '0.85rem 2rem',
              borderRadius: '8px',
              fontFamily:   'var(--font-heading)',
              fontSize:     '0.78rem',
              fontWeight:   700,
              cursor:       'pointer',
              transition:   'transform 0.2s, box-shadow 0.2s',
              letterSpacing: '0.05em',
              boxShadow:    '0 0 30px rgba(0,245,255,0.5)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.05) translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 0 60px rgba(0,245,255,0.8)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1) translateY(0)'
              e.currentTarget.style.boxShadow = '0 0 30px rgba(0,245,255,0.5)'
            }}
          >
            View Architecture
          </button>

          <button
            onClick={() => scrollTo('demo')}
            style={{
              background:   'transparent',
              border:       '1px solid rgba(0, 245, 255, 0.5)',
              color:        'var(--cyan)',
              padding:      '0.85rem 2rem',
              borderRadius: '8px',
              fontFamily:   'var(--font-heading)',
              fontSize:     '0.78rem',
              cursor:       'pointer',
              transition:   'background 0.2s, box-shadow 0.2s',
              letterSpacing: '0.05em',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(0,245,255,0.1)'
              e.currentTarget.style.boxShadow  = '0 0 30px rgba(0,245,255,0.3)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.boxShadow  = 'none'
            }}
          >
            Watch Demo
          </button>
        </div>

        {/* Interaction hint */}
        <p
          style={{
            fontFamily:  'var(--font-mono)',
            fontSize:    '0.65rem',
            color:       'rgba(0,245,255,0.35)',
            marginTop:   '1.2rem',
            letterSpacing: '0.08em',
            opacity:     btnVisible ? 1 : 0,
            transition:  'opacity 0.6s ease 0.6s',
            pointerEvents: 'none',
          }}
        >
          ✦ MOVE CURSOR OVER GLOBE TO SCATTER NODES
        </p>

        {/* Mini stats row */}
        <div
          style={{
            display:        'flex',
            gap:            '2rem',
            justifyContent: 'center',
            flexWrap:       'wrap',
            marginTop:      '3rem',
            opacity:        statsVis ? 1 : 0,
            transform:      statsVis ? 'none' : 'translateY(16px)',
            transition:     'opacity 0.6s ease, transform 0.6s ease',
          }}
        >
          {MINI_STATS.map(({ value, label }) => (
            <div
              key={label}
              style={{ textAlign: 'center' }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize:   'clamp(1.4rem, 3vw, 1.9rem)',
                  color:      'var(--cyan)',
                  textShadow: '0 0 20px rgba(0,245,255,0.5)',
                  lineHeight: 1,
                }}
              >
                {value}
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize:   '0.68rem',
                  color:      'var(--text-muted)',
                  marginTop:  '0.3rem',
                  letterSpacing: '0.05em',
                }}
              >
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Scroll indicator — restore pointer events for click */}
      <div
        style={{
          position:   'absolute',
          bottom:     '2rem',
          left:       '50%',
          transform:  'translateX(-50%)',
          zIndex:     2,
          opacity:    btnVisible ? 1 : 0,
          transition: 'opacity 0.6s ease 0.5s',
          pointerEvents: 'auto',
        }}
      >
        <div
          style={{
            color:     'var(--cyan)',
            fontSize:  '1.4rem',
            animation: 'bounce 1.8s ease-in-out infinite',
            cursor:    'pointer',
            textShadow: '0 0 15px var(--cyan)',
          }}
          onClick={() => scrollTo('architecture')}
        >
          ↓
        </div>
      </div>

      <style>{`
        @media (max-width: 480px) {
          .hero-globe-wrap > div {
            width: 95vw !important;
            height: 95vw !important;
          }
        }
      `}</style>
    </section>
  )
}
