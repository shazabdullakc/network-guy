import { useRef, useState } from 'react'
import useIntersection from '../hooks/useIntersection'

// ─── Bonus items verified against actual code ──────────────────
const BONUSES = [
  {
    icon: '🤖',
    title: 'Multi-LLM Provider Support',
    verdict: 'IMPLEMENTED',
    file: 'llm.py',
    color: '#00f5ff',
    desc: 'Auto-detects available API keys and routes to the right provider. Priority: DeepSeek → Gemini → Groq → OpenRouter → Grok → Anthropic. Graceful fallback shows raw agent findings if no key is set.',
    detail: [
      'DeepSeek (deepseek-chat) — default, best free reasoning',
      'Gemini (gemini-2.5-flash) — Google free tier',
      'Groq (llama-3.3-70b-versatile) — fastest inference',
      'OpenRouter (deepseek-r1:free) — aggregator',
      'Grok (grok-3-mini) — xAI',
      'Anthropic (claude-sonnet-4) — highest quality',
    ],
  },
  {
    icon: '⌨️',
    title: 'Interactive REPL with Autocomplete',
    verdict: 'IMPLEMENTED',
    file: 'repl.py',
    color: '#00f5ff',
    desc: 'Claude Code-inspired interactive session built on prompt_toolkit. Tab-completion for all 10 slash commands. After /metrics or /blast, autocompletes 15 known device names. Inline command preview with description.',
    detail: [
      'Tab autocomplete for all slash commands',
      'Device name completion after /metrics and /blast',
      'In-memory command history (arrow up/down)',
      'Live status bar showing LLM provider + model',
      'Colored prompt: cyan ❯ in prompt_toolkit style',
    ],
  },
  {
    icon: '💾',
    title: 'Session Memory & Export',
    verdict: 'IMPLEMENTED',
    file: 'repl.py',
    color: '#00f5ff',
    desc: 'Every turn (query + response + latency + severity) is logged to a session history list. /history replays the session. /export writes a timestamped Markdown file with all turns, evidence, and remediation steps.',
    detail: [
      '/history — shows all turns with latency',
      '/export — writes session to .md file',
      'Timestamps and severity per turn',
      'Export includes full RCA + evidence + fix steps',
    ],
  },
  {
    icon: '📊',
    title: 'Statistical Anomaly Detection',
    verdict: 'IMPLEMENTED',
    file: 'agents/security/anomaly.py',
    color: '#7c3aed',
    desc: 'Z-score anomaly detection over SNMP time-series metrics. Flags readings more than 2.5σ from mean. Runs in parallel with signature engine — allows detecting novel attacks that don\'t match known signatures.',
    detail: [
      'Z-score analysis on CPU, memory, bandwidth',
      'Z-score threshold: 2.5σ (configurable)',
      'Complements signature engine (known + novel)',
      'Results fed to correlator for cross-referencing',
    ],
  },
  {
    icon: '📁',
    title: 'Custom Synthetic Security Dataset',
    verdict: 'IMPLEMENTED',
    file: 'data/',
    color: '#7c3aed',
    desc: 'Created two datasets beyond the 5 provided hackathon files: security_events.log (auth failures, port scans, flood alerts, config changes, rogue devices) and traffic_flows.csv (NetFlow records with source IPs, ports, flags, bytes).',
    detail: [
      'security_events.log — 7 attack type signatures',
      'traffic_flows.csv — NetFlow with attacker 10.99.0.0/16',
      'Realistic timestamps aligned with SNMP metrics',
      'Rogue MAC on SW-LAB-01 GE0/45',
    ],
  },
  {
    icon: '⛓️',
    title: 'Attack Chain Timeline Builder',
    verdict: 'IMPLEMENTED',
    file: 'agents/security/correlator.py',
    color: '#7c3aed',
    desc: 'Cross-references log events, security events, and SNMP metrics to build a sequential attack timeline. Output: Recon → Scan → Flood → Impact → Crash with timestamps and source attribution.',
    detail: [
      'Correlates 3 data sources (logs + security + metrics)',
      'Timestamps each attack phase',
      'Identifies primary attacker IP (10.99.1.15)',
      'Generates containment prioritization',
    ],
  },
]

// ─── Provider logos row (text-based) ───────────────────────────
const PROVIDERS = [
  { name: 'DeepSeek',   note: 'default · free',  cyan: true  },
  { name: 'Gemini',     note: '2.5-flash',        cyan: true  },
  { name: 'Groq',       note: 'llama-3.3-70b',   cyan: true  },
  { name: 'OpenRouter', note: 'r1:free',          cyan: false },
  { name: 'Grok',       note: 'grok-3-mini',     cyan: false },
  { name: 'Anthropic',  note: 'claude-sonnet-4', cyan: false },
]

// ─── Card component ────────────────────────────────────────────
function BonusCard({ icon, title, verdict, file, color, desc, detail, visible, delay }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      style={{
        background:   expanded ? 'rgba(0,245,255,0.06)' : 'rgba(0,245,255,0.025)',
        border:       `1px solid ${expanded ? 'rgba(0,245,255,0.4)' : 'rgba(0,245,255,0.12)'}`,
        borderRadius: '12px',
        padding:      '1.4rem',
        opacity:      visible ? 1 : 0,
        transform:    visible ? 'none' : 'translateY(24px)',
        transition:   `opacity 0.5s ease ${delay}ms, transform 0.5s ease ${delay}ms, border-color 0.2s, background 0.2s, box-shadow 0.2s`,
        boxShadow:    expanded ? 'var(--glow-cyan)' : 'none',
        cursor:       'pointer',
      }}
      onClick={() => setExpanded(e => !e)}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.9rem' }}>
        <span style={{ fontSize: '1.5rem', lineHeight: 1, flexShrink: 0 }}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '0.3rem' }}>
            <span style={{ fontFamily: 'var(--font-heading)', fontSize: '0.8rem', color: 'var(--text)', letterSpacing: '0.03em' }}>
              {title}
            </span>
            <span style={{
              fontFamily:   'var(--font-mono)',
              fontSize:     '0.58rem',
              letterSpacing: '0.06em',
              color:        '#00ff88',
              background:   'rgba(0,255,136,0.08)',
              border:       '1px solid rgba(0,255,136,0.2)',
              borderRadius: '3px',
              padding:      '0.1rem 0.4rem',
            }}>
              ✓ {verdict}
            </span>
          </div>
          <code style={{
            fontFamily:  'var(--font-mono)',
            fontSize:    '0.6rem',
            color:       'rgba(0,245,255,0.45)',
            background:  'rgba(0,245,255,0.05)',
            border:      '1px solid rgba(0,245,255,0.1)',
            borderRadius: '3px',
            padding:     '0.1rem 0.4rem',
          }}>
            {file}
          </code>
        </div>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize:   '0.7rem',
          color:      'rgba(0,245,255,0.4)',
          flexShrink: 0,
          transition: 'transform 0.2s',
          transform:  expanded ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>
          ▾
        </span>
      </div>

      {/* Description */}
      <p style={{
        fontFamily:   'var(--font-mono)',
        fontSize:     '0.73rem',
        color:        'var(--text-muted)',
        lineHeight:   1.6,
        marginTop:    '0.8rem',
        marginLeft:   '2.4rem',
      }}>
        {desc}
      </p>

      {/* Expanded detail */}
      {expanded && (
        <ul style={{
          marginTop:   '0.8rem',
          marginLeft:  '2.4rem',
          paddingLeft: '1rem',
          borderLeft:  '2px solid rgba(0,245,255,0.2)',
        }}>
          {detail.map((d, i) => (
            <li key={i} style={{
              fontFamily: 'var(--font-mono)',
              fontSize:   '0.68rem',
              color:      'rgba(0,245,255,0.6)',
              lineHeight: 1.7,
              listStyle:  'none',
              paddingLeft: '0.5rem',
            }}>
              <span style={{ color: 'rgba(0,245,255,0.3)', marginRight: '0.4rem' }}>▸</span>
              {d}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function BonusSection() {
  const sectionRef  = useRef(null)
  const providerRef = useRef(null)
  const cardsRef    = useRef(null)

  const isVisible   = useIntersection(sectionRef)
  const provVis     = useIntersection(providerRef)
  const cardsVis    = useIntersection(cardsRef)

  return (
    <section
      id="bonus"
      ref={sectionRef}
      style={{
        padding:    '7rem 2rem',
        background: 'linear-gradient(180deg, #001828 0%, #00080f 100%)',
        position:   'relative',
        zIndex:     1,
      }}
    >
      {/* ── Header ─────────────────────────────── */}
      <div style={{
        textAlign:    'center',
        marginBottom: '3.5rem',
        opacity:      isVisible ? 1 : 0,
        transform:    isVisible ? 'none' : 'translateY(24px)',
        transition:   'opacity 0.6s ease, transform 0.6s ease',
      }}>
        <span className="section-label">Bonus Challenges</span>
        <h2 className="section-title">Going Beyond the Requirements</h2>
        <p className="section-sub">
          Every bonus challenge — verified against the actual source code. Click a card for implementation details.
        </p>
      </div>

      {/* ── Multi-LLM provider strip ─────────────── */}
      <div ref={providerRef} style={{
        maxWidth:     '900px',
        margin:       '0 auto 3.5rem',
        opacity:      provVis ? 1 : 0,
        transition:   'opacity 0.6s ease',
      }}>
        <p style={{
          fontFamily:   'var(--font-heading)',
          fontSize:     '0.7rem',
          color:        'var(--text-muted)',
          textAlign:    'center',
          letterSpacing: '0.1em',
          marginBottom: '1rem',
        }}>
          6 LLM PROVIDERS — AUTO-DETECTED AT RUNTIME
        </p>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', justifyContent: 'center' }}>
          {PROVIDERS.map((p, i) => (
            <div
              key={p.name}
              style={{
                padding:     '0.5rem 1rem',
                borderRadius: '8px',
                border:      `1px solid ${p.cyan ? 'rgba(0,245,255,0.35)' : 'rgba(0,245,255,0.12)'}`,
                background:  p.cyan ? 'rgba(0,245,255,0.07)' : 'rgba(0,245,255,0.02)',
                opacity:     provVis ? 1 : 0,
                transform:   provVis ? 'none' : 'translateY(12px)',
                transition:  `opacity 0.4s ease ${i * 80}ms, transform 0.4s ease ${i * 80}ms`,
              }}
            >
              <div style={{ fontFamily: 'var(--font-heading)', fontSize: '0.7rem', color: p.cyan ? '#00f5ff' : 'var(--text-muted)', letterSpacing: '0.04em' }}>
                {p.name}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.58rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {p.note}
              </div>
            </div>
          ))}
        </div>
        <p style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'rgba(0,245,255,0.3)',
          textAlign: 'center', marginTop: '0.75rem', letterSpacing: '0.04em',
        }}>
          No API key? Raw agent findings are still shown — tool works fully offline.
        </p>
      </div>

      {/* ── Bonus cards ──────────────────────────── */}
      <div
        ref={cardsRef}
        style={{
          maxWidth:            '900px',
          margin:              '0 auto',
          display:             'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
          gap:                 '1rem',
        }}
      >
        {BONUSES.map((b, i) => (
          <BonusCard key={b.title} {...b} visible={cardsVis} delay={i * 90} />
        ))}
      </div>

      <style>{`
        @media (max-width: 640px) {
          #bonus > div:last-of-type { grid-template-columns: 1fr !important; }
          #bonus { padding: 4rem 1rem !important; }
        }
      `}</style>
    </section>
  )
}
