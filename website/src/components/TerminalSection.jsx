import { useEffect, useRef, useState, useCallback } from 'react'

// ─── Tab definitions ───────────────────────────────────────────
const TABS = [
  { id: 'repl',     label: '❯  REPL Session',       icon: '⚡' },
  { id: 'rca',      label: '🔍  RCA Query',           icon: '🔍' },
  { id: 'security', label: '🛡️  Security Scan',       icon: '🛡️' },
]

// ─── REPL welcome session ──────────────────────────────────────
const REPL_LINES = [
  { text: '── Network Guy v0.1.0 ──────────────────────────────────', cls: 'divider', delay: 200 },
  { text: '',                                                         cls: 'gap',     delay: 100 },
  { text: '  ┌─┐',                                                   cls: 'logo',    delay: 80  },
  { text: '  │N│ Network Guy',                                        cls: 'logo',    delay: 60  },
  { text: '  │G│ AI Troubleshooting Assistant',                       cls: 'logo',    delay: 60  },
  { text: '  └─┘',                                                   cls: 'logo',    delay: 60  },
  { text: '',                                                         cls: 'gap',     delay: 80  },
  { text: '  Provider   gemini-2.0-flash-exp',                       cls: 'meta',    delay: 80  },
  { text: '  Devices    15 loaded  (2 unhealthy)',                    cls: 'meta',    delay: 80  },
  { text: '  Incidents  3 open P1',                                   cls: 'meta',    delay: 80  },
  { text: '',                                                         cls: 'gap',     delay: 120 },
  { text: '  Tips for getting started',                               cls: 'header',  delay: 80  },
  { text: '  Ask a question like:',                                   cls: 'muted',   delay: 60  },
  { text: '  "Why did BGP drop on ROUTER-LAB-01?"',                   cls: 'cmd',     delay: 80  },
  { text: '',                                                         cls: 'gap',     delay: 80  },
  { text: '  Quick commands',                                         cls: 'header',  delay: 60  },
  { text: '  /devices  /incidents  /security-scan  /blast <device>',  cls: 'muted',   delay: 80  },
  { text: '',                                                         cls: 'gap',     delay: 100 },
  { text: '───────────────────────────────────────────────────────', cls: 'divider', delay: 80  },
  { text: '  ? for help                      gemini · flash-exp',    cls: 'status',  delay: 80  },
  { text: '───────────────────────────────────────────────────────', cls: 'divider', delay: 80  },
  { text: '',                                                         cls: 'gap',     delay: 200 },
  { text: '❯ Why did ROUTER-LAB-01 crash at 08:15?',                  cls: 'prompt',  delay: 300 },
  { text: '',                                                         cls: 'gap',     delay: 100 },
  { text: '  Analyzing...  ████████████████████████  (2.3s)',         cls: 'info',    delay: 600 },
]

// ─── Single RCA query output ───────────────────────────────────
const RCA_LINES = [
  { text: '❯ network-guy query "Why did ROUTER-LAB-01 crash?"',       cls: 'prompt',  delay: 300 },
  { text: '',                                                          cls: 'gap',     delay: 80  },
  { text: '  Running 5 agents...   (2.3s)',                           cls: 'info',    delay: 500 },
  { text: '',                                                          cls: 'gap',     delay: 80  },
  { text: '╔═══ Root Cause Analysis ═══════════════════════════════╗', cls: 'box',    delay: 200 },
  { text: '║                                                       ║', cls: 'box',    delay: 60  },
  { text: '║  Root Cause (Confidence: 92%)                         ║', cls: 'header', delay: 80  },
  { text: '║  Memory exhaustion → CPU spike →                      ║', cls: 'result', delay: 60  },
  { text: '║  BGP hold timer expiry → process crash                ║', cls: 'result', delay: 60  },
  { text: '║                                                       ║', cls: 'box',    delay: 40  },
  { text: '║  Evidence:                                            ║', cls: 'label',  delay: 80  },
  { text: '║  • CPU 92% at 08:15:00    [snmp_metrics.csv:14]      ║', cls: 'evidence',delay: 200 },
  { text: '║  • BGP dropped 08:15:03   [router_syslog.log:9]      ║', cls: 'evidence',delay: 200 },
  { text: '║  • 4523 pkt/s drops       [snmp_metrics.csv:16]      ║', cls: 'evidence',delay: 200 },
  { text: '║  • bgpd crashed 08:17:00  [router_syslog.log:14]     ║', cls: 'evidence',delay: 200 },
  { text: '║                                                       ║', cls: 'box',    delay: 40  },
  { text: '║  Security: ✅ LEGITIMATE FAILURE (not an attack)      ║', cls: 'secure', delay: 200 },
  { text: '║                                                       ║', cls: 'box',    delay: 40  },
  { text: '║  Fix:                                                 ║', cls: 'label',  delay: 80  },
  { text: '║  1. router bgp 65001 → bgp graceful-restart           ║', cls: 'fix',    delay: 200 },
  { text: '║  2. memory free low-watermark processor 20            ║', cls: 'fix',    delay: 200 },
  { text: '║                                                       ║', cls: 'box',    delay: 40  },
  { text: '║  Historical: INC-2024-0228-003  (similarity: 91%)     ║', cls: 'match',  delay: 200 },
  { text: '╚═══════════════════════════════════════════════════════╝', cls: 'box',    delay: 80  },
  { text: '',                                                          cls: 'gap',     delay: 80  },
  { text: '  Blast radius: SW-LAB-01, LB-LAB-01, FIREWALL-01',       cls: 'muted',   delay: 200 },
  { text: '  Severity: P1  |  Confidence: 92%',                       cls: 'muted',   delay: 100 },
]

// ─── Security scan output ──────────────────────────────────────
const SECURITY_LINES = [
  { text: '❯ network-guy security-scan',                              cls: 'prompt',  delay: 300 },
  { text: '',                                                          cls: 'gap',     delay: 80  },
  { text: '  Running security scan...   scanning 47 events',          cls: 'info',    delay: 600 },
  { text: '',                                                          cls: 'gap',     delay: 100 },
  { text: '╔═══ Security Verdict ══════════════════════════════════╗', cls: 'alert',  delay: 200 },
  { text: '║  🔴 ATTACK DETECTED                                   ║', cls: 'attack', delay: 200 },
  { text: '║  Confidence: 87%  |  Type: DDoS + Port Scan           ║', cls: 'attack', delay: 100 },
  { text: '╚═══════════════════════════════════════════════════════╝', cls: 'alert',  delay: 80  },
  { text: '',                                                          cls: 'gap',     delay: 100 },
  { text: '  Attack Chain:',                                           cls: 'label',   delay: 80  },
  { text: '  08:00  Recon — port scan from 10.99.1.15 (1,247 ports)', cls: 'chain',   delay: 200 },
  { text: '  08:05  Scan  — SSH brute force (312 failed logins)',      cls: 'chain',   delay: 200 },
  { text: '  08:10  Flood  — SYN flood 2.3 Gbps from 10.99.0.0/16',  cls: 'chain',   delay: 200 },
  { text: '  08:12  Impact — ROUTER-LAB-01 CPU saturated at 92%',     cls: 'chain',   delay: 200 },
  { text: '  08:15  Crash  — BGP session dropped (hold timer)',        cls: 'chain',   delay: 200 },
  { text: '',                                                          cls: 'gap',     delay: 100 },
  { text: '  Containment Steps:',                                      cls: 'label',   delay: 80  },
  { text: '  1.  ip access-list extended BLOCK-ATTACKER',             cls: 'fix',     delay: 200 },
  { text: '      deny ip 10.99.0.0 0.0.255.255 any',                  cls: 'fix',     delay: 100 },
  { text: '  2.  ip route 10.99.0.0 255.255.0.0 Null0',              cls: 'fix',     delay: 200 },
  { text: '  3.  storm-control broadcast level 20',                   cls: 'fix',     delay: 200 },
  { text: '',                                                          cls: 'gap',     delay: 100 },
  { text: '  Rogue device detected: Unknown MAC on SW-LAB-01 GE0/45', cls: 'warn',    delay: 200 },
]

const ALL_LINES = { repl: REPL_LINES, rca: RCA_LINES, security: SECURITY_LINES }

// ─── Color map ─────────────────────────────────────────────────
const COLOR = {
  prompt:  '#00f5ff',
  divider: 'rgba(0,245,255,0.3)',
  logo:    '#00f5ff',
  header:  '#00f5ff',
  meta:    '#8ab0c0',
  muted:   '#607080',
  status:  '#607080',
  info:    '#7c3aed',
  cmd:     '#e0f0ff',
  box:     'rgba(0,245,255,0.25)',
  label:   '#8ab0c0',
  result:  '#f0f0f8',
  evidence:'#c0d8e8',
  secure:  '#00ff88',
  fix:     '#e0e0e0',
  match:   '#ffd700',
  alert:   'rgba(255,80,80,0.5)',
  attack:  '#ff6060',
  chain:   '#ffaa60',
  warn:    '#ffd700',
}

const BRACKET_RE = /(\[[^\]]+\])/g
function parseLine(text, cls) {
  if (cls !== 'evidence') return text
  return text.split(BRACKET_RE).map((part, i) =>
    BRACKET_RE.test(part)
      ? <span key={i} style={{ color: '#ffd700', fontWeight: 'bold' }}>{part}</span>
      : part
  )
}

function TermLine({ line }) {
  if (line.cls === 'gap') return <div style={{ height: '0.45rem' }} />
  const color = COLOR[line.cls] || '#e0e0e0'
  return (
    <div style={{ color, whiteSpace: 'pre', lineHeight: 1.65, fontSize: '0.78rem' }}>
      {parseLine(line.text, line.cls)}
    </div>
  )
}

// ─── Main component ────────────────────────────────────────────
export default function TerminalSection() {
  const [activeTab,    setActiveTab]    = useState('rca')
  const [displayed,    setDisplayed]    = useState([])
  const [showCursor,   setShowCursor]   = useState(false)
  const timeoutIds = useRef([])
  const bodyRef    = useRef(null)

  const startTyping = useCallback((tab) => {
    setDisplayed([])
    setShowCursor(false)
    timeoutIds.current.forEach(id => clearTimeout(id))
    timeoutIds.current = []

    const lines = ALL_LINES[tab]
    let accumulated = 0

    lines.forEach((line, i) => {
      accumulated += line.delay
      const id = setTimeout(() => {
        setDisplayed(prev => [...prev, line])
        if (bodyRef.current) {
          bodyRef.current.scrollTop = bodyRef.current.scrollHeight
        }
      }, accumulated)
      timeoutIds.current.push(id)
    })

    const cursorId = setTimeout(() => setShowCursor(true), accumulated + 200)
    timeoutIds.current.push(cursorId)
  }, [])

  useEffect(() => {
    startTyping(activeTab)
    return () => timeoutIds.current.forEach(id => clearTimeout(id))
  }, [activeTab, startTyping])

  return (
    <section
      id="demo"
      style={{
        padding:    '7rem 2rem',
        background: 'linear-gradient(180deg, #001020 0%, #00080f 100%)',
        position:   'relative',
        zIndex:     1,
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <span className="section-label">Live Demo</span>
        <h2 className="section-title">See It In Action</h2>
        <p className="section-sub">Three real CLI sessions — from REPL startup to full RCA to attack detection</p>
      </div>

      <div style={{ maxWidth: '860px', margin: '0 auto' }}>
        {/* Tab bar */}
        <div style={{
          display:      'flex',
          gap:          '0.5rem',
          marginBottom: '0',
          flexWrap:     'wrap',
        }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background:   activeTab === tab.id ? 'rgba(0,245,255,0.12)' : 'rgba(0,245,255,0.03)',
                border:       `1px solid ${activeTab === tab.id ? 'rgba(0,245,255,0.6)' : 'rgba(0,245,255,0.15)'}`,
                borderBottom: activeTab === tab.id ? '1px solid #040e16' : '1px solid rgba(0,245,255,0.15)',
                color:        activeTab === tab.id ? '#00f5ff' : '#607080',
                fontFamily:   'var(--font-mono)',
                fontSize:     '0.75rem',
                padding:      '0.6rem 1.2rem',
                borderRadius: '8px 8px 0 0',
                cursor:       'pointer',
                transition:   'all 0.2s ease',
                letterSpacing: '0.03em',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Terminal window */}
        <div style={{
          borderRadius: '0 8px 12px 12px',
          boxShadow:    '0 0 60px rgba(0,245,255,0.12), 0 20px 60px rgba(0,0,0,0.6)',
          border:       '1px solid rgba(0,245,255,0.2)',
          overflow:     'hidden',
        }}>
          {/* MacOS chrome bar */}
          <div style={{
            background:  '#040e16',
            padding:     '0.7rem 1rem',
            display:     'flex',
            alignItems:  'center',
            gap:         '0.5rem',
            borderBottom: '1px solid rgba(0,245,255,0.1)',
          }}>
            {[['#ff5f57','close'],['#ffbd2e','min'],['#28c840','max']].map(([bg, lbl]) => (
              <span key={lbl} style={{ width: '11px', height: '11px', borderRadius: '50%', background: bg, display: 'inline-block' }} />
            ))}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: '#607080', marginLeft: '0.5rem' }}>
              network-guy
            </span>
            <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'rgba(0,245,255,0.4)' }}>
              {activeTab === 'repl' ? 'Interactive REPL Mode'
               : activeTab === 'rca' ? 'Single Query Mode'
               : 'Security Audit Mode'}
            </span>
          </div>

          {/* Terminal body */}
          <div
            ref={bodyRef}
            style={{
              background: '#040e16',
              padding:    '1.2rem 1.4rem',
              minHeight:  '460px',
              maxHeight:  '520px',
              overflowY:  'auto',
              overflowX:  'auto',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {displayed.map((line, i) => <TermLine key={i} line={line} />)}

            {showCursor && (
              <span style={{
                color:      '#00f5ff',
                textShadow: '0 0 10px #00f5ff',
                animation:  'blink 1s step-start infinite',
                fontSize:   '0.85rem',
              }}>
                █
              </span>
            )}
          </div>
        </div>

        {/* Replay button */}
        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <button
            onClick={() => startTyping(activeTab)}
            style={{
              background: 'transparent',
              border:     '1px solid rgba(0,245,255,0.3)',
              color:      'var(--cyan)',
              fontFamily: 'var(--font-heading)',
              fontSize:   '0.72rem',
              padding:    '0.6rem 1.8rem',
              borderRadius: '8px',
              cursor:     'pointer',
              transition: 'background 0.2s, box-shadow 0.2s',
              letterSpacing: '0.06em',
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
      </div>

      <style>{`
        @media (max-width: 600px) { #demo { padding: 4rem 1rem !important; } }
      `}</style>
    </section>
  )
}
