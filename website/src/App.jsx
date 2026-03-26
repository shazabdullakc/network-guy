import './index.css'
import Navbar              from './components/Navbar'
import HeroSection         from './components/HeroSection'
import StatsSection        from './components/StatsSection'
import ArchSection         from './components/ArchSection'
import CommandsSection     from './components/CommandsSection'
import BonusSection        from './components/BonusSection'
import DeliverablesSection from './components/DeliverablesSection'
import TerminalSection     from './components/TerminalSection'
import ParticleCanvas      from './canvas/ParticleCanvas'

export default function App() {
  return (
    <>
      <ParticleCanvas />
      <Navbar />
      <main style={{ position: 'relative', zIndex: 1 }}>
        <HeroSection />
        <StatsSection />
        <ArchSection />
        <CommandsSection />
        <BonusSection />
        <DeliverablesSection />
        <TerminalSection />
      </main>
    </>
  )
}
