import { useRef, useState } from 'react'
import useIntersection from '../hooks/useIntersection'

const AGENTS = [
  {
    icon: '📋',
    name: 'Log Analyst',
    desc: 'Semantic search over syslogs',
    detail: 'ChromaDB vector search over syslog events grouped by 5-min windows. Ranks by severity and extracts error timelines.',
    cyan: false,
  },
  {
    icon: '🔢',
    name: 'Metrics Agent',
    desc: 'SQL queries on SNMP time-series',
    detail: 'SQLite queries: CPU, memory, packet drops across time ranges. Detects spikes, threshold breaches, and trends.',
    cyan: false,
  },
  {
    icon: '🕸️',
    name: 'Topology Agent',
    desc: 'Graph BFS for blast radius',
    detail: 'NetworkX BFS/DFS from failed node. Computes downstream devices, affected MPLS paths, and redundancy loss.',
    cyan: false,
  },
  {
    icon: '📁',
    name: 'Incident Agent',
    desc: 'Historical correlation',
    detail: 'Semantic similarity over past incident tickets. Finds matching patterns and proven resolutions with confidence scores.',
    cyan: false,
  },
  {
    icon: '🛡️',
    name: 'Security Agent',
    desc: 'Attack vs failure detection',
    detail: '3-stage pipeline: signature scan (7 attack types) → anomaly detection → cross-correlation. Returns ATTACK / LEGITIMATE / INCONCLUSIVE.',
    cyan: true,
  },
]

const BOX_BASE = {
  display:         'inline-flex',
  alignItems:      'center',
  justifyContent:  'center',
  border:          '1px solid var(--border-cyan)',
  background:      'rgba(0, 245, 255, 0.06)',
  borderRadius:    '8px',
  fontFamily:      'var(--font-heading)',
  fontSize:        '0.72rem',
  color:           'var(--text)',
  padding:         '0.65rem 1.6rem',
  textAlign:       'center',
  letterSpacing:   '0.04em',
}

const CONNECTOR_V = {
  width:      '2px',
  height:     '40px',
  background: 'linear-gradient(#00f5ff, rgba(0,245,255,0.1))',
  margin:     '0 auto',
  boxShadow:  '0 0 6px rgba(0,245,255,0.4)',
}

function BranchConnector({ count }) {
  return (
    <div style={{ position: 'relative', height: '56px' }}>
      <div style={{
        position:   'absolute', top: 0,
        left:       `${100 / (count + 1)}%`,
        right:      `${100 / (count + 1)}%`,
        height:     '2px',
        background: 'linear-gradient(90deg, transparent, var(--cyan), transparent)',
        boxShadow:  '0 0 8px rgba(0,245,255,0.5)',
      }} />
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{
          position:   'absolute', top: 0,
          left:       `${((i + 1) / (count + 1)) * 100}%`,
          width:      '2px', height: '100%',
          background: 'linear-gradient(var(--cyan), rgba(0,245,255,0.1))',
          transform:  'translateX(-50%)',
          boxShadow:  '0 0 5px rgba(0,245,255,0.3)',
        }} />
      ))}
    </div>
  )
}

function MergeConnector({ count }) {
  return (
    <div style={{ position: 'relative', height: '56px' }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{
          position:   'absolute', bottom: 0,
          left:       `${((i + 1) / (count + 1)) * 100}%`,
          width:      '2px', height: '100%',
          background: 'linear-gradient(rgba(0,245,255,0.1), var(--cyan))',
          transform:  'translateX(-50%)',
          boxShadow:  '0 0 5px rgba(0,245,255,0.3)',
        }} />
      ))}
      <div style={{
        position:   'absolute', bottom: 0,
        left:       `${100 / (count + 1)}%`,
        right:      `${100 / (count + 1)}%`,
        height:     '2px',
        background: 'linear-gradient(90deg, transparent, var(--cyan), transparent)',
        boxShadow:  '0 0 8px rgba(0,245,255,0.5)',
      }} />
    </div>
  )
}

function AgentBox({ icon, name, desc, detail, cyan, visible, delay }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display:       'flex',
        flexDirection: 'column',
        alignItems:    'center',
        flex:          1,
        minWidth:      '140px',
        maxWidth:      '170px',
        padding:       hovered ? '1rem 0.8rem' : '1.2rem 1rem',
        borderRadius:  '12px',
        background:    hovered ? (cyan ? 'rgba(0,245,255,0.1)' : 'rgba(0,245,255,0.06)') : 'var(--card-bg)',
        border:        `1px solid ${cyan ? 'rgba(0,245,255,0.5)' : 'var(--border-cyan)'}`,
        transition:    `transform 0.35s ease, box-shadow 0.35s ease, opacity 0.5s ease ${delay}ms, background 0.25s ease, padding 0.25s ease`,
        cursor:        'default',
        transform:     !visible ? 'translateY(35px)' : hovered ? 'translateY(-10px)' : 'translateY(0)',
        boxShadow:     hovered
          ? (cyan ? '0 0 40px rgba(0,245,255,0.5)' : '0 0 30px rgba(0,245,255,0.3)')
          : 'none',
        opacity:       visible ? 1 : 0,
        position:      'relative',
        overflow:      'hidden',
      }}
    >
      {/* Shimmer on hover */}
      {hovered && (
        <div style={{
          position:   'absolute', inset: 0,
          background: 'linear-gradient(105deg, transparent 40%, rgba(0,245,255,0.08) 50%, transparent 60%)',
          backgroundSize: '200% 100%',
          animation:  'shimmer 1.2s linear infinite',
          pointerEvents: 'none',
        }} />
      )}

      <span style={{ fontSize: '1.7rem', marginBottom: '0.5rem' }}>{icon}</span>
      <span style={{
        fontFamily:    'var(--font-heading)',
        fontSize:      '0.68rem',
        color:         cyan ? 'var(--cyan)' : 'var(--text)',
        textAlign:     'center',
        letterSpacing: '0.04em',
      }}>
        {name}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize:   '0.6rem',
        color:      'var(--text-muted)',
        marginTop:  '0.35rem',
        textAlign:  'center',
        lineHeight: 1.4,
      }}>
        {hovered ? detail : desc}
      </span>
    </div>
  )
}

// Data store pill
function StorePill({ icon, name, desc }) {
  return (
    <div style={{
      display:     'flex',
      alignItems:  'center',
      gap:         '0.75rem',
      padding:     '0.8rem 1.2rem',
      borderRadius: '10px',
      border:      'var(--border-cyan) solid 1px',
      background:  'rgba(0,245,255,0.04)',
      flex:        1,
      minWidth:    '180px',
    }}>
      <span style={{ fontSize: '1.3rem' }}>{icon}</span>
      <div>
        <div style={{ fontFamily: 'var(--font-heading)', fontSize: '0.7rem', color: 'var(--cyan)' }}>{name}</div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{desc}</div>
      </div>
    </div>
  )
}

export default function ArchSection() {
  const sectionRef  = useRef(null)
  const agentRowRef = useRef(null)
  const storeRef    = useRef(null)
  const isVisible   = useIntersection(sectionRef)
  const agentRowVis = useIntersection(agentRowRef)
  const storeVis    = useIntersection(storeRef)

  return (
    <section
      id="architecture"
      ref={sectionRef}
      style={{
        padding:    '7rem 2rem',
        background: 'linear-gradient(180deg, #001420 0%, #00080f 100%)',
        position:   'relative',
        zIndex:     1,
      }}
    >
      {/* Header */}
      <div style={{
        textAlign:    'center',
        marginBottom: '3.5rem',
        opacity:      isVisible ? 1 : 0,
        transform:    isVisible ? 'none' : 'translateY(24px)',
        transition:   'opacity 0.6s ease, transform 0.6s ease',
      }}>
        <span className="section-label">System Architecture</span>
        <h2 className="section-title">How NetFix AI Thinks</h2>
        <p className="section-sub">
          Five specialized agents. Three data stores. One answer in 60 seconds.
        </p>
      </div>

      {/* Diagram */}
      <div style={{ maxWidth: '920px', margin: '0 auto' }}>

        <div style={{ textAlign: 'center' }}>
          <span style={{ ...BOX_BASE, padding: '0.65rem 2rem' }}>CLI Input — network-guy query "..."</span>
        </div>

        <div style={CONNECTOR_V} />

        <div style={{ textAlign: 'center' }}>
          <span style={{ ...BOX_BASE, padding: '0.65rem 2.8rem', border: '1px solid rgba(0,245,255,0.5)' }}>
            LangGraph Supervisor
          </span>
        </div>

        <BranchConnector count={5} />

        {/* Agent boxes */}
        <div
          ref={agentRowRef}
          style={{
            display:        'flex',
            gap:            '0.8rem',
            flexWrap:       'wrap',
            justifyContent: 'center',
          }}
        >
          {AGENTS.map((agent, i) => (
            <AgentBox
              key={agent.name}
              {...agent}
              visible={agentRowVis}
              delay={i * 120}
            />
          ))}
        </div>

        <MergeConnector count={5} />

        <div style={{ textAlign: 'center' }}>
          <span style={{ ...BOX_BASE, padding: '0.65rem 2.2rem' }}>
            LLM Synthesis — Claude · DeepSeek · Gemini · Groq
          </span>
        </div>

        <div style={CONNECTOR_V} />

        <div style={{ textAlign: 'center' }}>
          <span style={{
            ...BOX_BASE,
            border:     '1px solid rgba(0,245,255,0.7)',
            background: 'rgba(0,245,255,0.1)',
            color:      'var(--cyan)',
            padding:    '0.65rem 2.2rem',
            boxShadow:  'var(--glow-cyan)',
            animation:  isVisible ? 'pulse-glow 2.5s ease-in-out infinite' : 'none',
          }}>
            Evidence-Backed Answer ✓
          </span>
        </div>

        {/* Security callout */}
        <div style={{
          marginTop:    '2.5rem',
          padding:      '1.2rem 1.8rem',
          background:   'rgba(124, 58, 237, 0.08)',
          border:       '1px solid var(--border-purple)',
          borderRadius: '12px',
          fontFamily:   'var(--font-mono)',
          fontSize:     '0.85rem',
          color:        '#b89cff',
          lineHeight:   1.6,
          opacity:      isVisible ? 1 : 0,
          transform:    isVisible ? 'none' : 'translateY(20px)',
          transition:   'opacity 0.6s ease 0.5s, transform 0.6s ease 0.5s',
        }}>
          🔒 <strong>Security Agent is unique</strong> — we&apos;re the only team that detects whether
          a failure is an attack or a legitimate issue.
          Classifies 7 attack types including DDoS, BGP hijack, ARP spoofing, brute force, and rogue devices.
        </div>
      </div>

      {/* Data Stores */}
      <div style={{
        maxWidth:   '920px',
        margin:     '4rem auto 0',
        opacity:    isVisible ? 1 : 0,
        transition: 'opacity 0.7s ease 0.3s',
      }}>
        <h3 style={{
          fontFamily:   'var(--font-heading)',
          fontSize:     '1rem',
          color:        'var(--text-muted)',
          textAlign:    'center',
          marginBottom: '1.5rem',
          letterSpacing: '0.1em',
        }}>
          THREE DATA STORES
        </h3>
        <div ref={storeRef} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
          <StorePill
            icon="🔍"
            name="ChromaDB — Vector Store"
            desc="Syslogs · Incidents · Security events · Device metadata"
          />
          <StorePill
            icon="🗄️"
            name="SQLite — Metrics Store"
            desc="SNMP time-series · Traffic flows · Threshold alerts"
          />
          <StorePill
            icon="🕸️"
            name="NetworkX — Topology Graph"
            desc="BFS blast radius · MPLS paths · Redundancy analysis"
          />
        </div>
      </div>

      <style>{`@media (max-width:600px){#architecture{padding:4rem 1rem !important;}}`}</style>
    </section>
  )
}
