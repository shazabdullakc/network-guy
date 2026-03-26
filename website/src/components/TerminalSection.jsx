import { useEffect, useRef, useState, useCallback } from 'react'

// ─── Terminal lines data ───────────────────────────────────────
const LINES = [
  { text: '$ network-guy query "Why did ROUTER-LAB-01 crash?"', cls: 'cmd',     delay: 400  },
  { text: '',                                                    cls: 'gap',     delay: 100  },
  { text: '[searching syslogs...]',                              cls: 'info',    delay: 500  },
  { text: '[querying SNMP metrics...]',                          cls: 'info',    delay: 400  },
  { text: '[checking topology...]',                              cls: 'info',    delay: 400  },
  { text: '[scanning security events...]',                       cls: 'info',    delay: 400  },
  { text: '',                                                    cls: 'gap',     delay: 200  },
  { text: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',    cls: 'divider', delay: 100  },
  { text: 'ROOT CAUSE — Confidence: 92%',                        cls: 'header',  delay: 200  },
  { text: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',    cls: 'divider', delay: 100  },
  { text: 'Memory exhaustion → CPU spike → BGP hold timer expiry', cls: 'result', delay: 300 },
  { text: '',                                                    cls: 'gap',     delay: 100  },
  { text: 'EVIDENCE:',                                           cls: 'label',   delay: 200  },
  { text: '  • CPU hit 92% at 08:15:00    [snmp_metrics.csv:14]',  cls: 'evidence', delay: 300 },
  { text: '  • BGP dropped at 08:15:03    [router_syslog.log:9]',  cls: 'evidence', delay: 300 },
  { text: '  • bgpd crashed at 08:17:00   [router_syslog.log:14]', cls: 'evidence', delay: 300 },
  { text: '',                                                    cls: 'gap',     delay: 100  },
  { text: 'SECURITY: ✅ LEGITIMATE FAILURE (not an attack)',     cls: 'secure',  delay: 300  },
  { text: '',                                                    cls: 'gap',     delay: 100  },
  { text: 'FIX:',                                               cls: 'label',   delay: 200  },
  { text: '  1. router bgp 65001 → bgp graceful-restart',        cls: 'fix',     delay: 300  },
  { text: '  2. memory free low-watermark processor 20',          cls: 'fix',     delay: 300  },
  { text: '',                                                    cls: 'gap',     delay: 100  },
  { text: 'HISTORICAL MATCH: INC-2024-0228-003 (91% similarity)', cls: 'match',  delay: 300  },
  { text: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',    cls: 'divider', delay: 200  },
]

// ─── Color map by CSS class ───────────────────────────────────
const COLOR = {
  cmd:     '#00f5ff',
  info:    '#7c3aed',
  divider: 'rgba(0,245,255,0.4)',
  header:  '#00f5ff',
  result:  '#f0f0f8',
  label:   '#8ab0c0',
  evidence:'#c0d8e8',
  secure:  '#00ff88',
  fix:     '#e0e0e0',
  match:   '#ffd700',
}

// ─── Parse evidence line: highlight [brackets] in gold ────────
const BRACKET_RE = /(\[[^\]]+\])/g

function parseLine(text, cls) {
  if (cls !== 'evidence') return text

  const parts = text.split(BRACKET_RE)
  return parts.map((part, i) =>
    BRACKET_RE.test(part)
      ? <span key={i} style={{ color: '#ffd700' }}>{part}</span>
      : part
  )
}

// ─── Single rendered line ─────────────────────────────────────
function TermLine({ line }) {
  if (line.cls === 'gap') {
    return <div style={{ height: '0.5rem' }} />
  }

  const color   = COLOR[line.cls] || '#e0e0e0'
  const isBold  = line.cls === 'header'
  const content = parseLine(line.text, line.cls)

  return (
    <div
      style={{
        color,
        fontWeight:  isBold ? 'bold' : 'normal',
        whiteSpace:  'pre',
        lineHeight:  1.7,
      }}
    >
      {content}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────
export default function TerminalSection() {
  const [displayed,   setDisplayed]   = useState([])
  const [showCursor,  setShowCursor]  = useState(false)
  const timeoutIds = useRef([])
  const bodyRef    = useRef(null)

  const startTyping = useCallback(() => {
    setDisplayed([])
    setShowCursor(false)

    // Clear any old timeouts
    timeoutIds.current.forEach(id => clearTimeout(id))
    timeoutIds.current = []

    let accumulated = 0

    LINES.forEach((line, i) => {
      accumulated += line.delay
      const id = setTimeout(() => {
        setDisplayed(prev => [...prev, line])
        // Auto-scroll terminal body
        if (bodyRef.current) {
          bodyRef.current.scrollTop = bodyRef.current.scrollHeight
        }
      }, accumulated)
      timeoutIds.current.push(id)
    })

    // Show cursor after last line
    accumulated += 200
    const cursorId = setTimeout(() => setShowCursor(true), accumulated)
    timeoutIds.current.push(cursorId)
  }, [])

  // Start on mount
  useEffect(() => {
    startTyping()
    return () => {
      timeoutIds.current.forEach(id => clearTimeout(id))
    }
  }, [startTyping])

  const handleReplay = () => {
    timeoutIds.current.forEach(id => clearTimeout(id))
    timeoutIds.current = []
    startTyping()
  }

  return (
    <section
      id="demo"
      style={{
        padding:    '6rem 2rem',
        background: '#0a0010',
        position:   'relative',
        zIndex:     1,
      }}
    >
      <h2
        className="section-title"
        style={{ textAlign: 'center', marginBottom: '2.5rem' }}
      >
        See It In Action
      </h2>

      {/* Terminal window */}
      <div
        style={{
          maxWidth:     '820px',
          margin:       '0 auto',
          borderRadius: '12px',
          boxShadow:    '0 0 60px rgba(0,245,255,0.2), 0 20px 60px rgba(0,0,0,0.6)',
        }}
      >
        {/* Header bar */}
        <div
          style={{
            background:   '#0a1520',
            borderRadius: '12px 12px 0 0',
            padding:      '0.75rem 1.2rem',
            display:      'flex',
            alignItems:   'center',
            gap:          '0.6rem',
          }}
        >
          {[['#ff5f57', 'close'], ['#ffbd2e', 'min'], ['#28c840', 'max']].map(([bg, label]) => (
            <span
              key={label}
              title={label}
              style={{
                width:        '12px',
                height:       '12px',
                borderRadius: '50%',
                background:   bg,
                display:      'inline-block',
                flexShrink:   0,
              }}
            />
          ))}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize:   '0.8rem',
              color:      'var(--text-muted)',
              marginLeft: 'auto',
            }}
          >
            network-guy — bash
          </span>
        </div>

        {/* Terminal body */}
        <div
          ref={bodyRef}
          style={{
            background:   '#040e16',
            border:       '1px solid rgba(0, 245, 255, 0.2)',
            borderTop:    'none',
            borderRadius: '0 0 12px 12px',
            padding:      '1.5rem',
            minHeight:    '440px',
            maxHeight:    '560px',
            overflowY:    'auto',
            overflowX:    'auto',
            fontFamily:   'var(--font-mono)',
            fontSize:     '0.82rem',
            lineHeight:   1.7,
          }}
        >
          {displayed.map((line, i) => (
            <TermLine key={i} line={line} />
          ))}

          {/* Blinking cursor */}
          {showCursor && (
            <span
              style={{
                color:     'var(--cyan)',
                textShadow: '0 0 10px var(--cyan)',
                animation: 'blink 1s step-start infinite',
                fontSize:  '0.9rem',
              }}
            >
              █
            </span>
          )}
        </div>
      </div>

      {/* Replay button */}
      <div style={{ textAlign: 'center' }}>
        <button
          onClick={handleReplay}
          style={{
            display:      'inline-block',
            marginTop:    '1.5rem',
            background:   'transparent',
            border:       '1px solid rgba(0,245,255,0.4)',
            color:        'var(--cyan)',
            fontFamily:   'var(--font-heading)',
            fontSize:     '0.75rem',
            padding:      '0.6rem 2rem',
            borderRadius: '8px',
            cursor:       'pointer',
            transition:   'background 0.2s, box-shadow 0.2s',
            letterSpacing: '0.05em',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(0,245,255,0.08)'
            e.currentTarget.style.boxShadow  = 'var(--glow-cyan)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.boxShadow  = 'none'
          }}
        >
          ↺  REPLAY
        </button>
      </div>

      <style>{`
        @media (max-width: 600px) {
          #demo { padding: 4rem 1rem !important; }
        }
      `}</style>
    </section>
  )
}
