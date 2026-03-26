import { useEffect, useRef, useState } from 'react'
import useIntersection from '../hooks/useIntersection'

const CARDS = [
  { value: '2-4 hrs', label: 'wasted per outage',  type: 'string' },
  { value: 15,        label: 'devices to monitor', type: 'count', suffix: '+' },
  { value: 1,         label: 'expert bottleneck',  type: 'count', suffix: '' },
]

function StringCounter({ value, isVisible }) {
  const [displayed, setDisplayed] = useState('')
  useEffect(() => {
    if (!isVisible) return
    let i = 0
    const ids = []
    const step = () => {
      i++
      if (i <= value.length) {
        setDisplayed(value.slice(0, i))
        ids.push(setTimeout(step, 70))
      }
    }
    ids.push(setTimeout(step, 0))
    return () => ids.forEach(id => clearTimeout(id))
  }, [isVisible, value])
  return <>{displayed || ''}</>
}

function NumberCounter({ value, suffix, isVisible }) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!isVisible) return
    const duration = 1200
    const start = performance.now()
    let rafId
    const step = (now) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(eased * value))
      if (progress < 1) rafId = requestAnimationFrame(step)
    }
    rafId = requestAnimationFrame(step)
    return () => { if (rafId) cancelAnimationFrame(rafId) }
  }, [isVisible, value])
  return <>{count}{suffix}</>
}

function StatCard({ value, label, type, suffix, index }) {
  const ref = useRef(null)
  const isVisible = useIntersection(ref)
  const [hovered, setHovered] = useState(false)

  return (
    <div
      ref={ref}
      className="glass-card"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex:      1,
        minWidth:  '200px',
        maxWidth:  '280px',
        padding:   '2.5rem 2rem',
        textAlign: 'center',
        opacity:   isVisible ? 1 : 0,
        transform: isVisible
          ? (hovered ? 'translateY(-6px) scale(1.03)' : 'translateY(0)')
          : 'translateY(40px)',
        transition: `opacity 0.6s ease ${index * 0.12}s, transform 0.4s ease, box-shadow 0.3s ease`,
        boxShadow: hovered
          ? '0 0 50px rgba(0,245,255,0.6)'
          : 'var(--glow-cyan)',
      }}
    >
      <span
        style={{
          fontFamily:    'var(--font-heading)',
          fontSize:      '3rem',
          color:         'var(--cyan)',
          display:       'block',
          marginBottom:  '0.75rem',
          letterSpacing: '-0.02em',
          textShadow:    '0 0 20px rgba(0,245,255,0.4)',
          animation:     isVisible ? `counter-ping 0.4s ease ${index * 0.12 + 1.1}s` : 'none',
        }}
      >
        {type === 'string'
          ? <StringCounter value={value} isVisible={isVisible} />
          : <NumberCounter value={value} suffix={suffix} isVisible={isVisible} />
        }
      </span>
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize:   '0.85rem',
          color:      'var(--text-muted)',
          letterSpacing: '0.04em',
        }}
      >
        {label}
      </span>
    </div>
  )
}

export default function StatsSection() {
  const titleRef = useRef(null)
  const titleVis = useIntersection(titleRef)

  return (
    <section
      style={{
        padding:    '6rem 2rem',
        textAlign:  'center',
        background: 'linear-gradient(180deg, #00080f 0%, #001420 100%)',
        position:   'relative',
        zIndex:     1,
      }}
    >
      {/* Divider line */}
      <div
        style={{
          width:        '1px',
          height:       '60px',
          background:   'linear-gradient(var(--cyan), transparent)',
          margin:       '0 auto 3rem',
          boxShadow:    '0 0 10px var(--cyan)',
        }}
      />

      <div ref={titleRef}>
        <h2
          style={{
            fontFamily:   'var(--font-heading)',
            fontSize:     'clamp(1.3rem, 3vw, 1.9rem)',
            marginBottom: '0.75rem',
            color:        'var(--text)',
            opacity:      titleVis ? 1 : 0,
            transform:    titleVis ? 'none' : 'translateY(20px)',
            transition:   'opacity 0.6s ease, transform 0.6s ease',
          }}
        >
          The Real Cost of Network Downtime
        </h2>
        <p
          style={{
            color:        'var(--text-muted)',
            fontSize:     '0.9rem',
            marginBottom: '3rem',
            opacity:      titleVis ? 1 : 0,
            transition:   'opacity 0.6s ease 0.2s',
          }}
        >
          Why network engineers need AI-powered diagnostics
        </p>
      </div>

      <div
        style={{
          display:        'flex',
          gap:            '1.5rem',
          flexWrap:       'wrap',
          justifyContent: 'center',
        }}
      >
        {CARDS.map((card, i) => (
          <StatCard key={card.label} {...card} index={i} />
        ))}
      </div>
    </section>
  )
}
