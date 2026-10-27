import { Link } from 'react-router-dom'
import { ShieldCheck, FileSearch, RefreshCw, BadgeCheck, ArrowRight } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { shots } from '../data/images.js'
import { schemes } from '../data/schemes.js'
import Hero from '../components/Hero.jsx'
import TechnologySection from '../components/TechnologySection.jsx'
import AIShowcase from '../components/AIShowcase.jsx'
import LocationSection from '../components/LocationSection.jsx'
import SchemeCard from '../components/SchemeCard.jsx'
import Reveal from '../components/Reveal.jsx'
import Photo from '../components/Photo.jsx'

export default function Home() {
  const { t } = useApp()
  const trust = [[ShieldCheck, 'trust1'], [FileSearch, 'trust2'], [RefreshCw, 'trust3'], [BadgeCheck, 'trust4']]
  return (
    <>
      <Hero />
      <TechnologySection />
      <section className="section band"><div className="wrap"><Reveal><AIShowcase /></Reveal></div></section>
      <section className="section">
        <div className="wrap"><Reveal>
          <h2>{t('supportTitle')}</h2>
          <div className="scheme-grid">{schemes.map((s) => <SchemeCard key={s.id} scheme={s} />)}</div>
          <p className="center"><Link to="/schemes" className="btn btn-outline">{t('viewAll')} <ArrowRight size={16} /></Link></p>
        </Reveal></div>
      </section>
      <section className="section band"><div className="wrap"><Reveal><LocationSection /></Reveal></div></section>
      <section id="trust" className="section trust">
        <div className="trust-bg"><Photo {...shots.docs} /></div>
        <div className="wrap trust-in"><Reveal className="trust-grid">
          <div><h2>{t('trustTitle')}</h2><p className="sub">{t('trustText')}</p></div>
          <ul className="trust-list">{trust.map(([Icon, k]) => <li key={k}><Icon size={22} /> {t(k)}</li>)}</ul>
        </Reveal></div>
      </section>
    </>
  )
}
