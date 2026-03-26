import { useEffect, useRef } from 'react'

const PARTICLE_COUNT = 50

function makeParticle(vw, vh, index) {
  const isCyan = index % 3 !== 0
  return {
    x:       Math.random() * vw,
    y:       Math.random() * vh,
    vx:      (Math.random() - 0.5) * 0.18,
    vy:      (Math.random() - 0.5) * 0.18,
    size:    0.8 + Math.random() * 2.2,
    opacity: 0.12 + Math.random() * 0.32,
    color:   isCyan ? '#00f5ff' : '#7c3aed',
    pulseOffset: Math.random() * Math.PI * 2,
    pulseSpeed:  0.5 + Math.random() * 1.0,
  }
}

export default function ParticleCanvas() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let rafId = null
    let particles = []
    let vw = window.innerWidth
    let vh = window.innerHeight
    let t = 0

    function init() {
      vw = window.innerWidth
      vh = window.innerHeight
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width  = vw * dpr
      canvas.height = vh * dpr
      canvas.style.width  = vw + 'px'
      canvas.style.height = vh + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      particles = Array.from({ length: PARTICLE_COUNT }, (_, i) =>
        makeParticle(vw, vh, i)
      )
    }

    function draw() {
      ctx.clearRect(0, 0, vw, vh)
      t += 0.01

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy

        if (p.x < -5)    p.x = vw + 5
        if (p.x > vw + 5) p.x = -5
        if (p.y < -5)    p.y = vh + 5
        if (p.y > vh + 5) p.y = -5

        // Pulse opacity
        const pulse = 0.7 + Math.sin(t * p.pulseSpeed + p.pulseOffset) * 0.3
        ctx.globalAlpha = p.opacity * pulse
        ctx.fillStyle   = p.color
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fill()
      }

      ctx.globalAlpha = 1
      rafId = requestAnimationFrame(draw)
    }

    init()
    window.addEventListener('resize', init)
    rafId = requestAnimationFrame(draw)

    return () => {
      if (rafId) cancelAnimationFrame(rafId)
      window.removeEventListener('resize', init)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position:      'fixed',
        inset:         0,
        zIndex:        0,
        pointerEvents: 'none',
        width:         '100vw',
        height:        '100vh',
      }}
    />
  )
}
