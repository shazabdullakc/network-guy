import './index.css'
import Navbar           from './components/Navbar'
import HeroSection      from './components/HeroSection'
import StatsSection     from './components/StatsSection'
import ArchSection      from './components/ArchSection'
import CommandsSection  from './components/CommandsSection'
import TerminalSection  from './components/TerminalSection'
import ParticleCanvas   from './canvas/ParticleCanvas'

export default function App() {
  return (
    <>
      {/* Fixed background particle layer */}
      <ParticleCanvas />

      {/* Fixed top navbar */}
      <Navbar />

      {/* Page content sits above particles */}
      <main style={{ position: 'relative', zIndex: 1 }}>
        <HeroSection />
        <StatsSection />
        <ArchSection />
        <CommandsSection />
        <TerminalSection />
      </main>
    </>
  )
}
