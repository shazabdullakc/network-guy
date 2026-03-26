import { useEffect, useRef, useState } from 'react'

const N = 90                    // More nodes for the larger globe
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))

// ─── Build node array on a sphere ─────────────────────────────
function buildNodes(R) {
  const nodes = []
  for (let i = 0; i < N; i++) {
    const y3d   = 1 - (i / (N - 1)) * 2
    const r2d   = Math.sqrt(Math.max(0, 1 - y3d * y3d))
    const theta = GOLDEN_ANGLE * i

    // Base position on sphere surface
    const bx = r2d * Math.cos(theta) * R
    const by = y3d * R
    const bz = r2d * Math.sin(theta) * R

    nodes.push({
      bx, by, bz,          // base sphere position (never mutated)
      // Scatter state (3D displacement from base)
      sx: 0, sy: 0, sz: 0,   // current scatter
      vx: 0, vy: 0, vz: 0,   // scatter velocity
      // Visual
      pulse:      Math.random() * Math.PI * 2,
      pulseSpeed: 0.5 + Math.random() * 0.9,
      isPurple:   i % 5 === 0,
      size:       0.8 + Math.random() * 0.55,
    })
  }
  return nodes
}

// ─── Build edges between close nodes ──────────────────────────
function buildEdges(nodes, R) {
  const edges = []
  const threshold = R * 0.62
  for (let a = 0; a < nodes.length; a++) {
    for (let b = a + 1; b < nodes.length; b++) {
      const dx = nodes[a].bx - nodes[b].bx
      const dy = nodes[a].by - nodes[b].by
      const dz = nodes[a].bz - nodes[b].bz
      if (Math.sqrt(dx * dx + dy * dy + dz * dz) < threshold) {
        edges.push([a, b])
      }
    }
  }
  return edges
}

// ─── Perspective-project one 3D point ─────────────────────────
function project(x, y, z, rotY, rotX, R, W, H) {
  // Rotate Y
  const x1 = x * Math.cos(rotY) - z * Math.sin(rotY)
  const z1 = x * Math.sin(rotY) + z * Math.cos(rotY)
  // Rotate X
  const y1 =  y * Math.cos(rotX) - z1 * Math.sin(rotX)
  const z2 =  y * Math.sin(rotX) + z1 * Math.cos(rotX)
  // Perspective
  const fov   = 750
  const scale = fov / (fov + z2 + R * 1.0)
  return {
    sx: x1 * scale + W / 2,
    sy: y1 * scale + H / 2,
    scale,
    z: z2,
  }
}

// ─── Build star field — biased toward left/right flanks ───────
const STAR_COUNT = 200
function buildStars(W, H) {
  const stars = []
  let attempts = 0
  while (stars.length < STAR_COUNT && attempts < STAR_COUNT * 8) {
    attempts++
    const nx = Math.random()   // 0–1 normalized x
    const ny = Math.random()   // 0–1 normalized y

    // Probability drops toward horizontal center
    const distFromCenterX = Math.abs(nx - 0.5) * 2  // 0 at center → 1 at edges
    const edgeBias = 0.2 + distFromCenterX * 0.8     // 0.2 at center, 1.0 at edges
    if (Math.random() > edgeBias) continue

    // Three size tiers
    const tier = Math.random()
    const size = tier < 0.65 ? 0.4 + Math.random() * 0.5   // tiny  (65%)
               : tier < 0.92 ? 0.9 + Math.random() * 0.6   // small (27%)
               :                1.6 + Math.random() * 0.8   // medium (8%)

    // Color: mostly blue-white, rare cyan/purple accents
    const cr = Math.random()
    const color = cr < 0.06 ? '#00f5ff'
                : cr < 0.10 ? '#9b8fff'
                :              '#c8e8f0'

    stars.push({
      x:             nx * W,
      y:             ny * H,
      size,
      baseOpacity:   0.04 + Math.random() * 0.18,
      twinkleSpeed:  0.3 + Math.random() * 0.7,
      twinkleOffset: Math.random() * Math.PI * 2,
      color,
    })
  }
  return stars
}

// ─── Main component ────────────────────────────────────────────
export default function GlobeCanvas() {
  const canvasRef  = useRef(null)
  const stateRef   = useRef({})
  const [opacity, setOpacity] = useState(0)

  useEffect(() => {
    const id = setTimeout(() => setOpacity(1), 300)
    return () => clearTimeout(id)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let rafId = null
    let nodes = []
    let edges = []
    let stars = []
    let W = 0, H = 0, R = 0
    const dpr = Math.min(window.devicePixelRatio || 1, 2)

    // Globe rotation state
    let rotY = 0
    let rotX = 0.15
    let targetRotX = 0.15

    // Orbiting light
    let lightAngle = 0

    // Mouse position relative to canvas (null = outside)
    let mouseCanvasX = null
    let mouseCanvasY = null

    // Scroll-based recovery factor: 0 = fully recovered, 1 = allow scatter
    // Driven by window.scrollY relative to hero height
    let scrollRecovery = 1.0   // starts at 1 (hero in view, scatter allowed)

    // ── Resize handler ──────────────────────────────────────────
    function resize() {
      const rect = canvas.parentElement.getBoundingClientRect()
      W = rect.width
      H = rect.height
      canvas.width  = W * dpr
      canvas.height = H * dpr
      canvas.style.width  = W + 'px'
      canvas.style.height = H + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      // Large globe — 52% of the smaller dimension
      R = Math.min(W, H) * 0.52
      nodes = buildNodes(R)
      edges = buildEdges(nodes, R)
      stars = buildStars(W, H)
    }

    // ── Canvas mouse move → repulsion ──────────────────────────
    function onCanvasMouseMove(e) {
      const rect = canvas.getBoundingClientRect()
      mouseCanvasX = e.clientX - rect.left
      mouseCanvasY = e.clientY - rect.top
    }

    function onCanvasMouseLeave() {
      mouseCanvasX = null
      mouseCanvasY = null
    }

    // ── Window mouse move → parallax tilt ──────────────────────
    function onWindowMouseMove(e) {
      const cx = window.innerWidth  / 2
      const cy = window.innerHeight / 2
      targetRotX = 0.15 + ((e.clientY - cy) / cy) * 0.20
    }

    // ── Scroll → recovery factor ────────────────────────────────
    function onScroll() {
      const heroEl = canvas.closest('#hero') || canvas.parentElement.parentElement
      const heroHeight = heroEl ? heroEl.offsetHeight : window.innerHeight
      // scrollRecovery = 1 when at top (hero visible), 0 when scrolled past hero
      const rawT = window.scrollY / Math.max(heroHeight * 0.6, 1)
      // When scrolling BACK UP: rawT decreases, so scrollRecovery increases
      // We want scatter to reverse (lerp back to 0) as user scrolls up
      scrollRecovery = Math.max(0, Math.min(1, 1 - rawT))
    }

    // ── Main animation loop ─────────────────────────────────────
    let starT = 0
    function draw() {
      ctx.clearRect(0, 0, W, H)
      starT += 0.008

      // ══ Draw stars first (behind everything) ══
      for (const s of stars) {
        const twinkle = 0.55 + Math.sin(starT * s.twinkleSpeed + s.twinkleOffset) * 0.45
        const alpha = s.baseOpacity * twinkle
        ctx.globalAlpha = alpha
        ctx.fillStyle = s.color
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2)
        ctx.fill()

        // Faint cross-spike on the larger stars
        if (s.size > 1.2) {
          ctx.globalAlpha = alpha * 0.4
          ctx.strokeStyle = s.color
          ctx.lineWidth = 0.5
          const spike = s.size * 2.5
          ctx.beginPath()
          ctx.moveTo(s.x - spike, s.y)
          ctx.lineTo(s.x + spike, s.y)
          ctx.stroke()
          ctx.beginPath()
          ctx.moveTo(s.x, s.y - spike)
          ctx.lineTo(s.x, s.y + spike)
          ctx.stroke()
        }
      }
      ctx.globalAlpha = 1

      rotY += 0.003
      rotX += (targetRotX - rotX) * 0.04
      lightAngle += 0.010

      // Repulsion radius — 25% of canvas height so it scales with hero size
      const REPULSE_RADIUS  = H * 0.25
      const REPULSE_FORCE   = R * 0.018
      const SCATTER_DECAY   = 0.96       // how slowly scatter fades (close to 1 = stays longer)
      const VEL_DAMPING     = 0.88       // velocity damping
      const RECOVERY_SPEED  = 0.06       // how fast nodes recover when scrolled up

      // ── Update each node's scatter physics ──
      for (const n of nodes) {
        // Projected position using current scatter + base
        const px = n.bx + n.sx
        const py = n.by + n.sy
        const pz = n.bz + n.sz
        const proj = project(px, py, pz, rotY, rotX, R, W, H)

        // ── Cursor repulsion ──
        if (mouseCanvasX !== null && scrollRecovery > 0.05) {
          const dx = proj.sx - mouseCanvasX
          const dy = proj.sy - mouseCanvasY
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < REPULSE_RADIUS && dist > 0.5) {
            // Repulsion force — stronger when closer
            const strength = (1 - dist / REPULSE_RADIUS) * REPULSE_FORCE
            // Push in 3D: outward from globe center (in the current rotated frame)
            // Direction from globe center in 3D
            const len3 = Math.sqrt(n.bx * n.bx + n.by * n.by + n.bz * n.bz) || 1
            n.vx += (n.bx / len3) * strength
            n.vy += (n.by / len3) * strength
            n.vz += (n.bz / len3) * strength
            // Also add a little screen-plane push to spread nodes visually
            n.vx += (dx / dist) * strength * 0.3
            n.vy += (dy / dist) * strength * 0.3
          }
        }

        // ── Scroll recovery: lerp scatter back to 0 ──
        // scrollRecovery: 1 = hero in view (allow scatter), 0 = hero out of view
        // When user scrolls back up, scrollRecovery increases → dampen scatter
        if (scrollRecovery < 0.98) {
          // The less recovery, the more aggressively we pull back
          const pullStrength = (1 - scrollRecovery) * RECOVERY_SPEED
          n.sx *= (1 - pullStrength)
          n.sy *= (1 - pullStrength)
          n.sz *= (1 - pullStrength)
          n.vx *= (1 - pullStrength)
          n.vy *= (1 - pullStrength)
          n.vz *= (1 - pullStrength)
        }

        // ── Spring physics ──
        n.sx += n.vx
        n.sy += n.vy
        n.sz += n.vz
        // Slow decay even without pulling (nodes slowly drift back)
        n.vx *= VEL_DAMPING
        n.vy *= VEL_DAMPING
        n.vz *= VEL_DAMPING
        n.sx *= SCATTER_DECAY
        n.sy *= SCATTER_DECAY
        n.sz *= SCATTER_DECAY

        // Clamp max scatter to 2.5× radius (nodes stay visible in full-hero canvas)
        const sLen = Math.sqrt(n.sx * n.sx + n.sy * n.sy + n.sz * n.sz)
        if (sLen > R * 2.5) {
          const scale = (R * 2.5) / sLen
          n.sx *= scale; n.sy *= scale; n.sz *= scale
          n.vx *= scale; n.vy *= scale; n.vz *= scale
        }
      }

      // ── Project all nodes (with scatter applied) ──
      const projected = nodes.map(n =>
        project(n.bx + n.sx, n.by + n.sy, n.bz + n.sz, rotY, rotX, R, W, H)
      )

      // ── Sort back → front ──
      const order = projected
        .map((p, i) => ({ i, z: p.z }))
        .sort((a, b) => a.z - b.z)
        .map(o => o.i)

      // ── Draw edges ──
      for (const [a, b] of edges) {
        const pa = projected[a]
        const pb = projected[b]
        if (pa.z < -R * 0.4 && pb.z < -R * 0.4) continue

        // Edge opacity based on depth AND scatter: scattered nodes make edges transparent
        const scatterA = Math.sqrt(nodes[a].sx ** 2 + nodes[a].sy ** 2 + nodes[a].sz ** 2) / R
        const scatterB = Math.sqrt(nodes[b].sx ** 2 + nodes[b].sy ** 2 + nodes[b].sz ** 2) / R
        const scatterFade = 1 - Math.min(1, (scatterA + scatterB) * 0.4)
        const depthAlpha = Math.max(0, Math.min(1, ((pa.z + pb.z) / 2 + R) / (2 * R)))
        const alpha = depthAlpha * scatterFade

        const isPurpleEdge = nodes[a].isPurple || nodes[b].isPurple
        ctx.beginPath()
        ctx.moveTo(pa.sx, pa.sy)
        ctx.lineTo(pb.sx, pb.sy)
        ctx.strokeStyle = isPurpleEdge
          ? `rgba(124, 58, 237, ${alpha * 0.5})`
          : `rgba(0, 210, 230, ${alpha * 0.45})`
        ctx.lineWidth = 0.65
        ctx.stroke()
      }

      // ── Draw nodes (back → front) ──
      for (const idx of order) {
        const n = nodes[idx]
        const p = projected[idx]

        n.pulse += n.pulseSpeed * 0.016
        const pulse  = 0.65 + Math.sin(n.pulse) * 0.35
        const isCyan = !n.isPurple
        const color   = isCyan ? '#00f5ff' : '#7c3aed'
        const glowClr = isCyan ? 'rgba(0,245,255,' : 'rgba(124,58,237,'

        // Scattered nodes glow brighter
        const scatter3d = Math.sqrt(n.sx ** 2 + n.sy ** 2 + n.sz ** 2) / R
        const scatterGlow = 1 + scatter3d * 1.5

        const r = p.scale * 5 * pulse * n.size

        // Outer radial glow (larger when scattered)
        const haloR = r * 3.5 * scatterGlow
        const grad = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, haloR)
        grad.addColorStop(0, glowClr + `${0.22 * scatterGlow})`)
        grad.addColorStop(1, glowClr + '0)')
        ctx.beginPath()
        ctx.arc(p.sx, p.sy, haloR, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()

        // Core dot
        ctx.beginPath()
        ctx.arc(p.sx, p.sy, r * Math.max(1, scatterGlow * 0.7), 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.shadowBlur = isCyan ? 8 : 6
        ctx.shadowColor = color
        ctx.fill()
        ctx.shadowBlur = 0
      }

      // ── Orbiting light ──
      const lx = Math.sin(lightAngle) * R * 1.3 + W / 2
      const ly = Math.cos(lightAngle * 0.55) * R * 0.45 + H / 2
      const lightGrad = ctx.createRadialGradient(lx, ly, 0, lx, ly, R * 0.55)
      lightGrad.addColorStop(0, 'rgba(0, 245, 255, 0.065)')
      lightGrad.addColorStop(1, 'rgba(0, 245, 255, 0)')
      ctx.beginPath()
      ctx.arc(lx, ly, R * 0.55, 0, Math.PI * 2)
      ctx.fillStyle = lightGrad
      ctx.fill()

      rafId = requestAnimationFrame(draw)
    }

    resize()

    // Attach events
    canvas.addEventListener('mousemove',  onCanvasMouseMove)
    canvas.addEventListener('mouseleave', onCanvasMouseLeave)
    window.addEventListener('mousemove',  onWindowMouseMove)
    window.addEventListener('resize',     resize)
    window.addEventListener('scroll',     onScroll, { passive: true })

    rafId = requestAnimationFrame(draw)

    return () => {
      if (rafId) cancelAnimationFrame(rafId)
      canvas.removeEventListener('mousemove',  onCanvasMouseMove)
      canvas.removeEventListener('mouseleave', onCanvasMouseLeave)
      window.removeEventListener('mousemove',  onWindowMouseMove)
      window.removeEventListener('resize',     resize)
      window.removeEventListener('scroll',     onScroll)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        display:    'block',
        width:      '100%',
        height:     '100%',
        opacity,
        transition: 'opacity 1s ease',
        // pointer-events AUTO so canvas catches cursor for repulsion
        // but we also listen on window for parallax, so both work
        pointerEvents: 'auto',
        cursor:     'crosshair',
      }}
    />
  )
}
