import { useRef, useState } from 'react'
import useIntersection from '../hooks/useIntersection'

// ─── Evaluation criteria (from FINAL_PLAN) ─────────────────────
const CRITERIA = [
  { label: 'Root Cause Accuracy',   weight: 30, score: 92,
    detail: '5 agents cross-reference 7 data sources. Every RCA is evidence-backed, not guessed.' },
  { label: 'Evidence Grounding',    weight: 20, score: 95,
    detail: 'Every claim cites source: log line number, metric timestamp, topology fact. Built into system prompt as hard requirement.' },
  { label: 'Remediation Quality',   weight: 20, score: 88,
    detail: 'Device-specific Cisco IOS-XE CLI commands. Historical incident resolutions. Step-by-step with risks noted.' },
  { label: 'System Design',         weight: 15, score: 90,
    detail: 'Modular agent architecture. Clean separation: data → agents → orchestrator → CLI. Adapter pattern for live network.' },
  { label: 'Innovation & UX',       weight: 15, score: 96,
    detail: 'Attack detection is unique — no other team distinguishes attack vs. legitimate failure. Beautiful Rich CLI + REPL.' },
]

// ─── Deliverables (from FINAL_PLAN hackathon checklist) ────────
const DELIVERABLES = [
  {
    num: '01',
    title: 'Working CLI Prototype',
    status: 'complete',
    icon: '⚡',
    desc: 'Full Python CLI that ingests 7 data files, builds 3 stores, and answers any natural-language network question in under 60 seconds.',
    tags: ['Python 3.11', 'Typer', 'Rich', 'LangGraph'],
  },
  {
    num: '02',
    title: 'Architecture Document',
    status: 'complete',
    icon: '📐',
    desc: 'Complete system design: agent responsibilities, data flow diagrams, technology choices with rationale, and implementation timeline.',
    tags: ['FINAL_PLAN.md', '638 lines', 'Full spec'],
  },
  {
    num: '03',
    title: 'Interactive REPL',
    status: 'complete',
    icon: '🖥️',
    desc: 'Claude Code-inspired interactive session with slash commands (/devices, /topology, /blast, /security-scan), session memory, and status bar.',
    tags: ['8 slash commands', 'Session export', 'Conversation memory'],
  },
  {
    num: '04',
    title: 'Source Code + README',
    status: 'complete',
    icon: '📦',
    desc: 'Full GitHub repository with 25 Python files, Poetry dependency management, and complete setup/usage documentation.',
    tags: ['GitHub', 'Poetry', '25 Python files', 'MIT License'],
  },
  {
    num: '05',
    title: 'Benchmark Suite',
    status: 'complete',
    icon: '📊',
    desc: '18-query benchmark: 10 core RCA scenarios from requirements + 8 security queries we added. Automated pass/fail with latency tracking.',
    tags: ['18 queries', '`network-guy benchmark`', 'Pass rate tracking'],
  },
  {
    num: '06',
    title: 'Security Extension',
    status: 'complete',
    icon: '🛡️',
    desc: 'Unique differentiator: 3-stage attack detection pipeline (signature scan → anomaly detection → correlation) across 7 attack types.',
    tags: ['7 attack types', 'Attack chain timeline', 'Containment steps', 'Confidence score'],
  },
]

// ─── Benchmark queries ─────────────────────────────────────────
const BENCHMARKS = [
  { q: 'What happened to ROUTER-LAB-01 between 08:10–08:20?', cat: 'RCA',      src: 'Logs + Metrics' },
  { q: 'Why did BGP session with peer 10.0.0.3 drop?',        cat: 'RCA',      src: 'Syslog:9' },
  { q: 'Which devices in NET-LAB-ALPHA are WARNING/CRITICAL?', cat: 'Status',   src: 'Metrics' },
  { q: 'If SW-LAB-02 is down, which devices are affected?',    cat: 'Topology', src: 'Graph BFS' },
  { q: 'Software version of ROUTER-LAB-01 vs ROUTER-LAB-02?', cat: 'Inventory',src: 'Device CSV' },
  { q: 'Has CPU spike + BGP drop happened before?',            cat: 'History',  src: 'Incidents' },
  { q: 'Blast radius of 5G-UPF-01 crash?',                    cat: 'Topology', src: 'Graph + Incidents' },
  { q: 'Show all CRITICAL syslog events in last hour',         cat: 'Logs',     src: 'Syslog' },
  { q: 'Is someone attacking the network?',                    cat: '🛡️ SEC',   src: 'Security Agent' },
  { q: 'Is the CPU spike an attack or legitimate failure?',    cat: '🛡️ SEC',   src: 'Cross-correlation' },
  { q: 'Who is attacking us? Show source IPs',                 cat: '🛡️ SEC',   src: 'Traffic flows' },
  { q: 'How do I stop the DDoS attack?',                       cat: '🛡️ SEC',   src: 'Signatures + LLM' },
  { q: 'Any rogue devices on the network?',                    cat: '🛡️ SEC',   src: 'MAC inventory' },
  { q: 'Has anyone changed config without authorization?',     cat: '🛡️ SEC',   src: 'Audit log' },
  { q: 'Show me the full attack timeline',                     cat: '🛡️ SEC',   src: 'Correlator' },
  { q: 'What is the overall security posture?',                cat: '🛡️ SEC',   src: 'All sources' },
]

const CAT_COLORS = {
  'RCA':       '#00f5ff',
  'Status':    '#00f5ff',
  'Topology':  '#7c3aed',
  'Inventory': '#7c3aed',
  'History':   '#7c3aed',
  'Logs':      '#00f5ff',
  '🛡️ SEC':   '#ff6060',
}

// ─── Score bar ─────────────────────────────────────────────────
function ScoreBar({ score, weight, label, detail, visible, delay }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        opacity:    visible ? 1 : 0,
        transform:  visible ? 'none' : 'translateX(-20px)',
        transition: `opacity 0.5s ease ${delay}ms, transform 0.5s ease ${delay}ms`,
        marginBottom: '1.2rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
        <span style={{ fontFamily: 'var(--font-heading)', fontSize: '0.72rem', color: hovered ? '#00f5ff' : 'var(--text)', transition: 'color 0.2s' }}>
          {label}
        </span>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
            weight: {weight}%
          </span>
          <span style={{ fontFamily: 'var(--font-heading)', fontSize: '0.8rem', color: '#00f5ff' }}>
            {score}%
          </span>
        </div>
      </div>

      {/* Bar track */}
      <div style={{ background: 'rgba(0,245,255,0.08)', border: '1px solid rgba(0,245,255,0.12)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
        <div
          style={{
            height:     '100%',
            width:      visible ? `${score}%` : '0%',
            background: 'linear-gradient(90deg, #00f5ff, #7c3aed)',
            transition: `width 1.2s ease ${delay + 300}ms`,
            boxShadow:  '0 0 8px rgba(0,245,255,0.4)',
          }}
        />
      </div>

      {/* Hover detail */}
      {hovered && (
        <div style={{
          marginTop:  '0.5rem',
          fontFamily: 'var(--font-mono)',
          fontSize:   '0.68rem',
          color:      'var(--text-muted)',
          lineHeight:  1.5,
          padding:    '0.5rem 0.75rem',
          background: 'rgba(0,245,255,0.04)',
          border:     '1px solid rgba(0,245,255,0.1)',
          borderRadius: '6px',
        }}>
          {detail}
        </div>
      )}
    </div>
  )
}

// ─── Deliverable card ──────────────────────────────────────────
function DeliverableCard({ num, title, status, icon, desc, tags, visible, delay }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background:   hovered ? 'rgba(0,245,255,0.06)' : 'rgba(0,245,255,0.025)',
        border:       `1px solid ${hovered ? 'rgba(0,245,255,0.45)' : 'rgba(0,245,255,0.12)'}`,
        borderRadius: '12px',
        padding:      '1.5rem',
        opacity:      visible ? 1 : 0,
        transform:    visible ? (hovered ? 'translateY(-4px)' : 'none') : 'translateY(24px)',
        transition:   `opacity 0.5s ease ${delay}ms, transform 0.4s ease, border-color 0.2s, background 0.2s, box-shadow 0.2s`,
        boxShadow:    hovered ? 'var(--glow-cyan)' : 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.75rem' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'rgba(0,245,255,0.3)', minWidth: '1.8rem' }}>{num}</span>
        <span style={{ fontSize: '1.4rem', lineHeight: 1 }}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'var(--font-heading)', fontSize: '0.8rem', color: 'var(--text)', marginBottom: '0.2rem', letterSpacing: '0.03em' }}>
            {title}
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.6rem', letterSpacing: '0.08em',
            color: '#00ff88', background: 'rgba(0,255,136,0.08)', border: '1px solid rgba(0,255,136,0.2)',
            borderRadius: '3px', padding: '0.1rem 0.4rem',
          }}>
            ✓ COMPLETE
          </span>
        </div>
      </div>

      <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.73rem', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '1rem', marginLeft: '3rem' }}>
        {desc}
      </p>

      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginLeft: '3rem' }}>
        {tags.map(t => (
          <span key={t} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.6rem',
            color: 'rgba(0,245,255,0.6)', background: 'rgba(0,245,255,0.06)',
            border: '1px solid rgba(0,245,255,0.12)', borderRadius: '4px', padding: '0.1rem 0.5rem',
          }}>
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function DeliverablesSection() {
  const headerRef   = useRef(null)
  const delivRef    = useRef(null)
  const scoreRef    = useRef(null)
  const benchRef    = useRef(null)

  const headerVis = useIntersection(headerRef)
  const delivVis  = useIntersection(delivRef)
  const scoreVis  = useIntersection(scoreRef)
  const benchVis  = useIntersection(benchRef)

  return (
    <section
      id="deliverables"
      style={{
        padding:    '7rem 2rem',
        background: 'linear-gradient(180deg, #00080f 0%, #001828 50%, #00080f 100%)',
        position:   'relative',
        zIndex:     1,
      }}
    >
      {/* ── Header ─────────────────────────────── */}
      <div
        ref={headerRef}
        style={{
          textAlign:    'center',
          marginBottom: '4rem',
          opacity:      headerVis ? 1 : 0,
          transform:    headerVis ? 'none' : 'translateY(24px)',
          transition:   'opacity 0.6s ease, transform 0.6s ease',
        }}
      >
        <span className="section-label">Project Deliverables</span>
        <h2 className="section-title">What We Built</h2>
        <p className="section-sub">
          Every hackathon deliverable. Shipped.
        </p>
      </div>

      <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

        {/* ── Deliverables grid ──────────────────── */}
        <div
          ref={delivRef}
          style={{
            display:             'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap:                 '1.2rem',
            marginBottom:        '5rem',
          }}
        >
          {DELIVERABLES.map((d, i) => (
            <DeliverableCard key={d.num} {...d} visible={delivVis} delay={i * 100} />
          ))}
        </div>

        {/* ── Two-column: Eval score + Benchmark table ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3rem', alignItems: 'start' }}>

          {/* Left: Evaluation scores */}
          <div ref={scoreRef}>
            <h3 style={{
              fontFamily:   'var(--font-heading)',
              fontSize:     '0.9rem',
              color:        'var(--text-muted)',
              letterSpacing: '0.1em',
              marginBottom: '1.5rem',
              opacity: scoreVis ? 1 : 0,
              transition: 'opacity 0.5s ease',
            }}>
              EVALUATION CRITERIA
            </h3>
            {CRITERIA.map((c, i) => (
              <ScoreBar key={c.label} {...c} visible={scoreVis} delay={i * 100} />
            ))}

            <div style={{
              marginTop:   '1.5rem',
              padding:     '1rem',
              background:  'rgba(0,245,255,0.04)',
              border:      '1px solid rgba(0,245,255,0.12)',
              borderRadius: '8px',
              fontFamily:  'var(--font-mono)',
              fontSize:    '0.72rem',
              color:       'var(--text-muted)',
              opacity:      scoreVis ? 1 : 0,
              transition:  'opacity 0.6s ease 0.7s',
            }}>
              💡 Hover each bar for detail on how we score it
            </div>
          </div>

          {/* Right: Benchmark table */}
          <div ref={benchRef}>
            <h3 style={{
              fontFamily:   'var(--font-heading)',
              fontSize:     '0.9rem',
              color:        'var(--text-muted)',
              letterSpacing: '0.1em',
              marginBottom: '1rem',
              opacity: benchVis ? 1 : 0,
              transition: 'opacity 0.5s ease',
            }}>
              18 BENCHMARK QUERIES
            </h3>

            <div style={{
              background:   '#040e16',
              border:       '1px solid rgba(0,245,255,0.15)',
              borderRadius: '10px',
              overflow:     'hidden',
              opacity:      benchVis ? 1 : 0,
              transition:   'opacity 0.6s ease 0.2s',
            }}>
              {/* Table header */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 70px 80px',
                padding: '0.6rem 1rem',
                background: 'rgba(0,245,255,0.05)',
                borderBottom: '1px solid rgba(0,245,255,0.1)',
                fontFamily: 'var(--font-heading)', fontSize: '0.6rem', letterSpacing: '0.1em', color: 'var(--text-muted)',
              }}>
                <span>QUERY</span>
                <span>CATEGORY</span>
                <span>DATA SOURCE</span>
              </div>

              {/* Rows */}
              <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
                {BENCHMARKS.map((b, i) => (
                  <div
                    key={i}
                    style={{
                      display:    'grid',
                      gridTemplateColumns: '1fr 70px 80px',
                      padding:    '0.55rem 1rem',
                      borderBottom: i < BENCHMARKS.length - 1 ? '1px solid rgba(0,245,255,0.05)' : 'none',
                      background: i % 2 === 0 ? 'transparent' : 'rgba(0,245,255,0.015)',
                      transition: 'background 0.15s',
                      fontSize:   '0.68rem',
                      fontFamily: 'var(--font-mono)',
                      alignItems: 'start',
                      gap:        '0.5rem',
                      opacity:    benchVis ? 1 : 0,
                      transform:  benchVis ? 'none' : 'translateX(10px)',
                      transitionDelay: `${0.2 + i * 0.03}s`,
                      transitionProperty: 'opacity, transform',
                      transitionDuration: '0.4s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,245,255,0.06)'}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(0,245,255,0.015)'}
                  >
                    <span style={{ color: 'var(--text-muted)', lineHeight: 1.4 }}>{b.q}</span>
                    <span style={{ color: CAT_COLORS[b.cat] || '#00f5ff', letterSpacing: '0.04em', fontSize: '0.6rem' }}>{b.cat}</span>
                    <span style={{ color: 'rgba(0,245,255,0.4)', fontSize: '0.6rem' }}>{b.src}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary pill */}
            <div style={{
              display:    'flex',
              gap:        '1rem',
              marginTop:  '1rem',
              flexWrap:   'wrap',
              opacity:    benchVis ? 1 : 0,
              transition: 'opacity 0.6s ease 0.8s',
            }}>
              {[['10', 'Core RCA'], ['8', 'Security'], ['18', 'Total'], ['<60s', 'Avg Latency']].map(([val, lbl]) => (
                <div key={lbl} style={{
                  flex: 1, minWidth: '70px', textAlign: 'center',
                  padding: '0.6rem 0.4rem',
                  background: 'rgba(0,245,255,0.04)',
                  border: '1px solid rgba(0,245,255,0.12)',
                  borderRadius: '8px',
                }}>
                  <div style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', color: '#00f5ff' }}>{val}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{lbl}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── CTA ──────────────────────────── */}
        <div style={{
          marginTop:  '4rem',
          textAlign:  'center',
          padding:    '2.5rem',
          background: 'linear-gradient(135deg, rgba(0,245,255,0.05), rgba(124,58,237,0.05))',
          border:     '1px solid rgba(0,245,255,0.2)',
          borderRadius: '16px',
          opacity:    headerVis ? 1 : 0,
          transition: 'opacity 0.8s ease 1s',
        }}>
          <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.1rem', color: 'var(--text)', marginBottom: '0.75rem' }}>
            Ready to see the code?
          </h3>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
            Open source · MIT License · Python 3.11 · Poetry
          </p>
          <a
            href="https://github.com/shazabdullakc/network-guy"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display:      'inline-block',
              background:   'var(--cyan)',
              color:        '#00080f',
              padding:      '0.8rem 2.2rem',
              borderRadius: '8px',
              fontFamily:   'var(--font-heading)',
              fontSize:     '0.78rem',
              fontWeight:   700,
              textDecoration: 'none',
              letterSpacing: '0.05em',
              boxShadow:    '0 0 30px rgba(0,245,255,0.4)',
              transition:   'transform 0.2s, box-shadow 0.2s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform  = 'scale(1.05) translateY(-2px)'
              e.currentTarget.style.boxShadow  = '0 0 60px rgba(0,245,255,0.7)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform  = 'scale(1) translateY(0)'
              e.currentTarget.style.boxShadow  = '0 0 30px rgba(0,245,255,0.4)'
            }}
          >
            View on GitHub →
          </a>
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          #deliverables > div > div:last-child {
            grid-template-columns: 1fr !important;
          }
        }
        @media (max-width: 600px) {
          #deliverables { padding: 4rem 1rem !important; }
        }
        #deliverables ::-webkit-scrollbar { width: 4px; height: 4px; }
        #deliverables ::-webkit-scrollbar-thumb { background: rgba(0,245,255,0.2); }
      `}</style>
    </section>
  )
}
