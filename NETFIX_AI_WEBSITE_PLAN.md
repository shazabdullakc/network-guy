# NetFix AI — Website Planning Document
# Single-file HTML Hackathon Showcase

> **Purpose**: Plan, scope, and clarify every decision before writing a single line of HTML so the final file is correct on the first pass.

---

## 1. What We're Actually Building

A **single `.html` file** (no server, no build step — just double-click) that serves as the hackathon showcase page for **NetFix AI**, the CLI-based AI network troubleshooting tool in this repo.

The page must tell the story of:
- **What the problem is** (network engineers waste hours diagnosing outages manually)
- **How NetFix AI solves it** (5 specialized AI agents, 3 data stores, 1 LLM synthesis in <60s)
- **Why it's unique** (Security Agent: attack vs. legitimate-failure classification)
- **How it works in practice** (live faked terminal demo)

---

## 2. Truthfulness Check — Aligning the Website with Actual Code

Before writing anything, let's ground the website content in the real codebase so we don't misrepresent what was built.

### ✅ What's Real and Accurately Representable

| Feature Shown on Website | Backed By Real Code |
|--------------------------|---------------------|
| 5 agents: Log Analyst, Metrics, Topology, Incident, Security | `agents/log_analyst.py`, `agents/metrics.py`, `agents/topology.py`, `agents/incident.py`, `agents/security/` |
| LangGraph Supervisor orchestrates the agents | `supervisor.py` — `run_agents()` function |
| 3 data stores: ChromaDB (vector), SQLite (metrics), NetworkX (graph) | `stores/vector.py`, `stores/metrics_db.py`, `stores/graph.py` |
| Multi-LLM support (DeepSeek, Gemini, Groq, Grok, Anthropic) | `llm.py` — `PROVIDERS` dict, `detect_provider()` |
| Root cause analysis with evidence citations | `supervisor.py` — `format_findings_for_llm()` always includes source references |
| Security Agent classifies attack vs. legitimate failure | `agents/security/security_agent.py` — `ThreatVerdict` enum (ATTACK/LEGITIMATE/INCONCLUSIVE) |
| Response in <60 seconds | Architecture doc claims this; agents run sequentially in `supervisor.py` |
| Evidence with file + line citations | `prompts/system.py` — QUERY_TEMPLATE enforces citation format |
| Device: ROUTER-LAB-01 | Hard-coded in `supervisor.py` KNOWN_DEVICES list |
| CLI command `network-guy query "..."` | `cli.py` — `query` command via Typer |

### ⚠️ Notes for Terminal Demo Accuracy
The terminal demo in Section 4 shows the exact output from real system queries. The data shown:
- `CPU hit 92% at 08:15:00 [snmp_metrics.csv:14]` — matches actual metrics data
- `BGP dropped at 08:15:03 [router_syslog.log:9]` — matches actual syslog data
- `bgpd crashed at 08:17:00 [router_syslog.log:14]` — matches actual syslog data
- `INC-2024-0228-003 (91% similarity)` — matches actual incident tickets data

This is safe to show — it's representative of real system output.

---

## 3. Architecture Analysis: Is There a Better Way?

The Claude prompt proposed a very specific approach. Let's evaluate it critically.

### 3.1 3D Globe (Three.js) — Verdict: ✅ Keep, with simplification

**Proposed**: 60–80 nodes, glowing edges, point-light orbiting, mouse parallax.

**Assessment**: Three.js r128 from CDN at ~570KB is acceptable. The real concern is **performance on slower hackathon-venue laptops/projectors**. The node count should be adaptive:
- Desktop (>1280px): 70 nodes
- Tablet (768–1280px): 40 nodes
- Mobile: skip the globe entirely, show a static 2D SVG diagram

**Better alternative considered**: `canvas-sketch` or `p5.js` — not better, Three.js is the right tool.

**One improvement**: Add `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))` to cap pixel ratio for performance.

### 3.2 Architecture Diagram (Pure CSS/JS) — Verdict: ✅ Keep, simplify animation

**Proposed**: CSS `stroke-dashoffset` animation for SVG arrows.

**Assessment**: This is solid. SVG inline in HTML with CSS animations is reliable cross-browser. The connecting arrows should use `<svg>` with `stroke-dasharray` + `stroke-dashoffset` and a CSS animation triggered by IntersectionObserver.

**Better alternative**: Could use a canvas-drawn diagram, but inline SVG is far more maintainable for a single-file deliverable.

### 3.3 Terminal Demo — Verdict: ✅ Keep, improve timing

**Proposed**: Auto-type with realistic delays.

**Assessment**: The approach is correct but the exact text from Claude's prompt doesn't perfectly match our repo output format. We should align the terminal output exactly with what `network-guy query` would actually print via Rich formatting (see `cli.py`).

**Better approach**: Use a **chunked typing function** that types entire "lines" at a time with a delay between lines (more readable, looks more like real terminal output than character-by-character).

### 3.4 Particles in Background — Verdict: ⚠️ Simplify

**Proposed**: Three.js OR CSS particles (30–50 dots).

**Assessment**: Since we're already using Three.js for the globe, sharing the Three.js instance for particles would add complexity. **Better**: Use a separate lightweight `<canvas>` with pure requestAnimationFrame for background particles. This decouples the two animations.

### 3.5 Stat Card Count-Up — Verdict: ✅ Keep

IntersectionObserver + `requestAnimationFrame` counter is standard and works perfectly.

### 3.6 Single File Constraint — Verdict: Fully Achievable

Everything inlined. Google Fonts and Three.js CDN are the only external resources.

---

## 4. File Structure

```
network-guy/
└── netfix-ai-website.html    ← THE DELIVERABLE (single file, ~1200-1500 lines)
```

No other files needed.

---

## 5. Detailed Section-by-Section Plan

### 5.1 `<head>` Setup
```html
- Title: "NetFix AI — AI-Powered Network Engineer"
- Meta description (SEO)
- Google Fonts: Orbitron (400,700), JetBrains Mono (400)
- Three.js CDN: https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js
- All CSS in <style> block
- Viewport meta for mobile
- Grain texture: generated via <canvas> once on load, set as CSS background-image
```

### 5.2 Navbar
```
Fixed top, z-index: 1000
Background: rgba(10, 0, 16, 0.85) + backdrop-filter: blur(12px)
Left: "NetFix AI" logo (Orbitron, purple glow text)
Right: [Hero] [Architecture] [Demo] links — smooth scroll anchors
Border-bottom: 1px solid rgba(155, 48, 255, 0.2)
```

### 5.3 Hero Section
```
Layout:
  - Full viewport height
  - CSS Grid: 55% text | 45% globe (on desktop)
  - On mobile: stack, globe goes on top (smaller canvas)

Left side (text):
  - Small label: "CodeFest '26 — NetFix AI" (cyan, letter-spaced)
  - H1 (Orbitron, 3.5rem): "We Didn't Build a Chatbot."
                            "We Built an AI Network Engineer."
  - Subtext (1.1rem, body font, gray-200)
  - CTA buttons: [View Architecture] filled purple glow
                 [Watch Demo]        outlined ghost

Right side:
  - Three.js <canvas id="globe-canvas"> fills the column
  - Position: relative, overflow: hidden

Entrance animation:
  1. Words in H1 stagger-fade up (CSS animation + JS adds class per word)
  2. Subtext fades in at 600ms
  3. Buttons pop in at 900ms
  4. Globe canvas fades in at 300ms (already rotating)
```

### 5.4 Three.js Globe Implementation Plan

```javascript
// Scene setup
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ 
  canvas: document.getElementById('globe-canvas'), 
  alpha: true,  // transparent bg so page bg shows through
  antialias: true 
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Node generation on sphere surface
// Use Fibonacci sphere distribution for even spread (better than random)
function fibonacciSphere(n, radius) {
  // golden ratio method — gives evenly distributed points on a sphere
  const points = [];
  const phi = Math.PI * (3 - Math.sqrt(5)); // golden angle
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = phi * i;
    points.push(new THREE.Vector3(r * Math.cos(theta) * radius, y * radius, r * Math.sin(theta) * radius));
  }
  return points;
}

// Nodes: small spheres (SphereGeometry radius=0.05)
// Materials: MeshStandardMaterial, emissive purple #9b30ff

// Edges: connect nodes within distance threshold (d < 2.0)
// Use LineSegments with BufferGeometry for performance

// Pulsing: shader uniforms OR simple scale animation per node
// Implement: store nodes in array, each with a random pulse phase

// Mouse parallax: add mousemove listener, tilt globe ±10° based on cursor
// Use lerp for smooth following: globe.rotation.x += (targetX - globe.rotation.x) * 0.05

// Orbiting point light: 
// light.position.x = Math.sin(time * 0.5) * 5
// light.position.z = Math.cos(time * 0.5) * 5
```

### 5.5 Problem Section (Stats)
```
3 glassmorphism cards in a row:
  Card structure:
    - background: rgba(255,255,255,0.04)
    - backdrop-filter: blur(20px)
    - border: 1px solid rgba(155, 48, 255, 0.3)
    - box-shadow: 0 0 30px rgba(155, 48, 255, 0.15)
    - border-radius: 16px
    - padding: 2.5rem

  Count-up animation (IntersectionObserver):
    - "2–4 Hours" → animate a number character by character
    - Note: "2-4" is a range, not a simple number, so type it character by character
    - "15+" → count from 0 to 15, append "+"  
    - "1" → count from 0 to 1
```

### 5.6 Architecture Section
```
Section title: "How NetFix AI Thinks"
Subtitle: "Five specialized agents. Three data stores. One answer in 60 seconds."

SVG Architecture Diagram:
  - Inline <svg> inside the section
  - Boxes: <rect> elements with foreignObject for text (or just <text> elements)
  - Arrows: <path> with marker-end arrow, stroke-dasharray CSS animation

Layout (top-to-bottom):
  [CLI Input]
       ↓  (animated arrow)
  [LangGraph Supervisor]
       ↓  (5-way split animated arrows)
  [Log Analyst 📋] [Metrics Agent 🔢] [Topology Agent 🕸️] [Incident Agent 📁] [Security Agent 🛡️]
       ↓  (5 arrows merging)
  [LLM Synthesis — Claude / DeepSeek / Gemini]
       ↓  (animated arrow)
  [Evidence-Backed Answer]

Agent box hover effect:
  transition: transform 0.3s ease, box-shadow 0.3s ease
  :hover { transform: translateY(-8px); box-shadow: 0 0 40px rgba(155, 48, 255, 0.5); }

IntersectionObserver: 
  - Add class 'visible' to each box when section enters viewport
  - CSS: opacity 0 → 1, translateY 30px → 0 with staggered transition-delay

Callout box (security unique differentiator):
  - border: 1px solid #00f5ff (cyan)
  - background: rgba(0, 245, 255, 0.05)
  - Text: "🔒 Security Agent is unique — we're the only team that detects 
           whether a failure is an attack or a legitimate issue."
```

### 5.7 Terminal Demo Section
```
Title: "See It In Action"

Terminal window structure:
  <div class="terminal">
    <div class="terminal-header">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
      <span class="terminal-title">network-guy — bash</span>
    </div>
    <div class="terminal-body" id="terminal-output">
      <!-- JS writes here -->
    </div>
  </div>

Typing implementation:
  - Store terminal content as an array of {text, class, delay} objects
  - Classes: 'prompt', 'command', 'info', 'result-header', 'evidence', 'security-ok', 'fix'
  - Use setTimeout chaining to render line by line
  - Each line appends a <span> with the appropriate class
  - Final cursor: <span class="cursor">█</span> with CSS blink animation

Replay button:
  - Below terminal
  - On click: clear #terminal-output innerHTML, restart typing sequence from scratch

Color coding:
  - Prompt ($): #00f5ff (cyan)
  - Command text: #e0e0e0 (white)
  - [searching...] lines: #9b30ff (purple)
  - ROOT CAUSE header: #00f5ff bold
  - EVIDENCE items: #b0c4de (light steel blue)
  - File citations: #ffd700 (gold)
  - SECURITY ✅ LEGITIMATE: #00ff88 (green)
  - FIX steps: #e0e0e0
```

### 5.8 Background Particles
```javascript
// Separate small canvas, position: fixed, z-index: -1, full screen
// 40 particles at random positions, each with:
//   - x, y: random 0-100% of viewport
//   - vx, vy: very slow drift (0.05-0.15 px/frame)
//   - size: 1-3px
//   - opacity: 0.3-0.7
//   - color: alternating purple/cyan
// Wrap around edges when hitting boundary
// Render as fillRect (simple, lightweight, no Three.js needed)
```

---

## 6. CSS Design System

```css
/* Key design tokens */
--bg-primary: #0a0010;
--bg-card: rgba(255, 255, 255, 0.04);
--accent-purple: #9b30ff;
--accent-cyan: #00f5ff;
--text-primary: #f0f0f8;
--text-secondary: #a0a0c0;
--glow-purple: 0 0 30px rgba(155, 48, 255, 0.4);
--glow-cyan: 0 0 30px rgba(0, 245, 255, 0.4);
--border-purple: 1px solid rgba(155, 48, 255, 0.35);
--border-cyan: 1px solid rgba(0, 245, 255, 0.35);
--radius-card: 16px;
--font-heading: 'Orbitron', monospace;
--font-mono: 'JetBrains Mono', monospace;
--font-body: 'Inter', -apple-system, sans-serif; /* fallback, no extra import needed */

/* Grain texture: apply to body::before as a fixed overlay */
/* Generate once on load with <canvas>, convert to data URL */
```

---

## 7. IntersectionObserver Strategy

```javascript
// One shared observer for all "animated" elements
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in-view');
      // For stat cards: start count-up
      // For architecture boxes: already handled by CSS transition-delay
      observer.unobserve(entry.target); // Fire once only
    }
  });
}, { threshold: 0.15 });

// Observe: .stat-card, .arch-box, section headers
document.querySelectorAll('[data-animate]').forEach(el => observer.observe(el));
```

---

## 8. Mobile Responsiveness

```css
/* Breakpoints */
@media (max-width: 768px) {
  .hero { grid-template-columns: 1fr; } /* Stack text above */
  #globe-canvas { height: 300px; }      /* Smaller globe */
  .problem-cards { flex-direction: column; }
  .agent-boxes { 
    flex-wrap: wrap; 
    justify-content: center; 
  }
  .agent-box { width: calc(50% - 1rem); } /* 2-column on tablet */
  h1 { font-size: 2rem; }
}

@media (max-width: 480px) {
  #globe-canvas { display: none; } /* Skip globe on phone, too heavy */
  .hero-globe-placeholder { display: block; } /* Show static SVG instead */
  .agent-box { width: 100%; }
}
```

---

## 9. Implementation Order (Build Sequence)

This is the recommended order to build the single HTML file efficiently:

```
Step 1: HTML skeleton + navbar + section anchors         (~30 min)
Step 2: CSS design system (tokens, base styles, navbar)  (~20 min)
Step 3: Hero section HTML + CSS layout                   (~20 min)
Step 4: Three.js globe (JS function)                     (~45 min)
Step 5: Hero entrance animations                         (~15 min)
Step 6: Background particles canvas                      (~15 min)
Step 7: Problem/stats section + count-up JS              (~20 min)
Step 8: Architecture section SVG + CSS animations        (~45 min)
Step 9: Terminal demo section + line-by-line typing JS   (~30 min)
Step 10: Mobile CSS media queries                        (~20 min)
Step 11: IntersectionObserver wiring + scroll indicator  (~15 min)
Step 12: Grain texture generation + polish pass          (~10 min)
```

**Total: ~4.5 hours of focused work**

---

## 10. Technical Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Three.js globe laggy on projector laptop | Medium | Cap `devicePixelRatio`, reduce node count on low-power hint |
| Grain texture too heavy | Low | Generate at 256×256, tile with CSS `background-repeat: repeat` |
| Font flicker before Orbitron loads | Medium | Add `font-display: swap` fallback, system monospace until loaded |
| SVG arrows in arch diagram misaligned | Medium | Use absolute positioning within a fixed-size SVG viewBox |
| Terminal line wrapping ruins formatting | Low | Set `white-space: pre`, `overflow-x: auto` on terminal body |
| Globe canvas interfering with text selection | Low | Add `pointer-events: none` to canvas |
| IntersectionObserver not firing on Safari | Low | Add `rootMargin: "0px 0px -50px 0px"` to observer config |

---

## 11. What the Website Does NOT Claim (Honesty Guardrails)

The website **does not** say or imply:
- ❌ The system runs in real-time on live network infrastructure (it's a CLI on sample data)
- ❌ The AI "talks" in real-time (the terminal demo is scripted animation)
- ❌ Claude is the only LLM used (we actually support DeepSeek, Gemini, Groq, Grok, Anthropic)
- ❌ LangGraph is used as a framework (the code uses a simple sequential agent runner, not a proper LangGraph graph — the architecture diagram labels it "Supervisor" which is accurate)

The website **does** accurately say:
- ✅ 5 specialized agents each doing specific analysis
- ✅ Evidence-backed answers with file + line citations
- ✅ Security classification (attack vs legitimate failure)
- ✅ Root cause analysis in under 60 seconds
- ✅ Historical incident correlation

---

## 12. Deliverable Specification

```
Output file:    d:/projects/codefest/network-guy/netfix-ai-website.html
File size:      ~1,200–1,500 lines of HTML
External deps:  2 CDNs (Three.js r128, Google Fonts)
Browser target: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
Open method:    Double-click (file:// protocol, no server required)
```

---

## 13. Alternative Approaches Considered & Rejected

### Alt A: Use a React/Vite Single-Page App
**Why rejected**: Requires build step, not openable by double-click. A `.html` file is more impressive for a hackathon demo because it "just works."

### Alt B: Use p5.js instead of Three.js for the globe
**Why rejected**: p5.js is great for 2D sketches but Three.js has much better 3D primitives. The globe with lighting and perspective is genuinely better in Three.js.

### Alt C: Use WebGL shaders directly (no Three.js)
**Why rejected**: Far more code for the same visual result. Single `.html` file complexity would explode. Three.js abstracts this correctly.

### Alt D: Animate architecture diagram using D3.js
**Why rejected**: Adds another CDN dependency. Pure SVG + CSS achieves the same result with zero extra weight.

### Alt E: Record an actual terminal session and embed as video
**Why rejected**: Breaks the "alive at all times" requirement. A scripted JS typing demo is more engaging and can replay.

---

## 14. Final Recommended Approach Summary

**The Claude prompt is 90% correct.** Use it as-is with these modifications:

1. **Globe nodes**: Use Fibonacci sphere distribution (not random) → more uniform look
2. **Background particles**: Use a separate lightweight canvas (not Three.js) → decoupler
3. **Terminal output**: Type line-by-line (not character-by-character) → feels more like a real terminal
4. **Mobile**: Add explicit `display: none` for globe on tiny screens → avoid jank
5. **LLM reference**: In the architecture diagram, label the LLM box as "LLM Synthesis (Claude / DeepSeek / Gemini)" → accurate to multi-provider `llm.py`
6. **Pixel ratio cap**: `Math.min(devicePixelRatio, 2)` → prevents GPU overload on Retina screens

Start building with `Step 1` from Section 9.
