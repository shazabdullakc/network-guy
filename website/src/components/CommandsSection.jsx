import { useRef, useState } from 'react'
import useIntersection from '../hooks/useIntersection'

const COMMANDS = [
  {
    cmd: 'network-guy',
    sub: '',
    desc: 'Launch the interactive REPL — Claude Code-inspired interface with session memory, status bar, and slash commands.',
    icon: '⚡',
  },
  {
    cmd: 'network-guy',
    sub: 'query "..."',
    desc: 'Single-shot natural language question. Runs all 5 agents and returns RCA with evidence citations in seconds.',
    icon: '🔍',
  },
  {
    cmd: 'network-guy',
    sub: 'security-scan',
    desc: 'Full security audit: runs signature matching, anomaly detection, and correlation across all data sources.',
    icon: '🛡️',
  },
  {
    cmd: 'network-guy',
    sub: 'benchmark',
    desc: 'Runs all 18 test queries (10 RCA + 8 security), reports pass rate, accuracy, and avg latency per query.',
    icon: '📊',
  },
]

const SLASH_CMDS = [
  { cmd: '/devices',              desc: 'List all 15 devices with status, version, uptime' },
  { cmd: '/topology',             desc: 'Display full network topology map' },
  { cmd: '/incidents',            desc: 'All open incidents with timeline & impact' },
  { cmd: '/security-scan',        desc: 'Run full security audit inline' },
  { cmd: '/metrics ROUTER-LAB-01',desc: 'Peak values + anomalies for a device' },
  { cmd: '/blast ROUTER-LAB-01',  desc: 'BFS blast radius calculation' },
  { cmd: '/history',              desc: 'Session turn log with latency & severity' },
  { cmd: '/export',               desc: 'Export session to Markdown file' },
]

function CommandCard({ cmd, sub, desc, icon, visible, delay }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding:     '1.5rem',
        borderRadius: '12px',
        border:      `1px solid ${hovered ? 'rgba(0,245,255,0.55)' : 'var(--border-cyan)'}`,
        background:  hovered ? 'rgba(0,245,255,0.06)' : 'var(--card-bg)',
        transition:  `opacity 0.5s ease ${delay}ms, transform 0.4s ease ${delay}ms, border-color 0.25s, background 0.25s, box-shadow 0.25s`,
        opacity:     visible ? 1 : 0,
        transform:   visible ? (hovered ? 'translateY(-5px)' : 'translateY(0)') : 'translateY(30px)',
        boxShadow:   hovered ? 'var(--glow-cyan)' : 'none',
        cursor:      'default',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '1.4rem' }}>{icon}</span>
        <code style={{
          fontFamily: 'var(--font-mono)',
          fontSize:   '0.8rem',
          color:      'var(--cyan)',
          background: 'rgba(0,245,255,0.08)',
          padding:    '0.25rem 0.75rem',
          borderRadius: '5px',
          border:     '1px solid rgba(0,245,255,0.2)',
        }}>
          {cmd}{sub ? ` ${sub}` : ''}
        </code>
      </div>
      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize:   '0.78rem',
        color:      'var(--text-muted)',
        lineHeight: 1.6,
      }}>
        {desc}
      </p>
    </div>
  )
}

export default function CommandsSection() {
  const sectionRef = useRef(null)
  const slashRef   = useRef(null)
  const isVisible  = useIntersection(sectionRef)
  const slashVis   = useIntersection(slashRef)

  return (
    <section
      id="commands"
      ref={sectionRef}
      style={{
        padding:    '7rem 2rem',
        background: 'linear-gradient(180deg, #00080f 0%, #001020 100%)',
        position:   'relative',
        zIndex:     1,
      }}
    >
      <div style={{
        textAlign:    'center',
        marginBottom: '3.5rem',
        opacity:      isVisible ? 1 : 0,
        transform:    isVisible ? 'none' : 'translateY(24px)',
        transition:   'opacity 0.6s ease, transform 0.6s ease',
      }}>
        <span className="section-label">CLI Reference</span>
        <h2 className="section-title">Every Way to Slice the Data</h2>
        <p className="section-sub">
          One tool. Multiple entry points. Zero guessing.
        </p>
      </div>

      {/* Main commands grid */}
      <div style={{
        display:             'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap:                 '1.2rem',
        maxWidth:            '900px',
        margin:              '0 auto 4rem',
      }}>
        {COMMANDS.map((c, i) => (
          <CommandCard key={c.sub} {...c} visible={isVisible} delay={i * 110} />
        ))}
      </div>

      {/* REPL slash commands */}
      <div
        ref={slashRef}
        style={{
          maxWidth:  '900px',
          margin:    '0 auto',
          opacity:   slashVis ? 1 : 0,
          transform: slashVis ? 'none' : 'translateY(24px)',
          transition: 'opacity 0.6s ease, transform 0.6s ease',
        }}
      >
        <h3 style={{
          fontFamily: 'var(--font-heading)',
          fontSize:   '0.9rem',
          color:      'var(--text-muted)',
          textAlign:  'center',
          marginBottom: '1.5rem',
          letterSpacing: '0.12em',
        }}>
          INTERACTIVE REPL — SLASH COMMANDS
        </h3>

        <div
          style={{
            background:   '#0d1520',
            border:       '1px solid var(--border-cyan)',
            borderRadius: '12px',
            overflow:     'hidden',
          }}
        >
          {/* Terminal header */}
          <div style={{
            background: '#0a1018',
            padding:    '0.65rem 1rem',
            display:    'flex',
            gap:        '0.5rem',
            alignItems: 'center',
            borderBottom: '1px solid rgba(0,245,255,0.1)',
          }}>
            {['#ff5f57','#ffbd2e','#28c840'].map(c => (
              <span key={c} style={{ width:'10px', height:'10px', borderRadius:'50%', background:c, display:'inline-block' }} />
            ))}
            <span style={{ fontFamily:'var(--font-mono)', fontSize:'0.75rem', color:'var(--text-muted)', marginLeft:'0.5rem' }}>
              network-guy — interactive session
            </span>
          </div>

          {/* Slash command list */}
          <div style={{ padding: '0.5rem 0' }}>
            {SLASH_CMDS.map(({ cmd, desc }, i) => (
              <div
                key={cmd}
                style={{
                  display:   'flex',
                  gap:       '1.5rem',
                  padding:   '0.6rem 1.2rem',
                  alignItems: 'baseline',
                  background: i % 2 === 0 ? 'transparent' : 'rgba(0,245,255,0.02)',
                  transition: 'background 0.2s',
                  opacity:   slashVis ? 1 : 0,
                  transition: `opacity 0.4s ease ${i * 70}ms`,
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,245,255,0.06)'}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(0,245,255,0.02)'}
              >
                <code style={{
                  fontFamily:  'var(--font-mono)',
                  fontSize:    '0.8rem',
                  color:       'var(--cyan)',
                  whiteSpace:  'nowrap',
                  minWidth:    '220px',
                }}>
                  {cmd}
                </code>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize:   '0.75rem',
                  color:      'var(--text-muted)',
                  lineHeight: 1.5,
                }}>
                  {desc}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
