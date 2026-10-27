import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { shots } from '../data/images.js'
import Photo from './Photo.jsx'

// Light hero: the photo sits softly (blurred, low opacity) behind the right side. Text stays on off-white.
export default function Hero() {
  const { t } = useApp()
  const [y, setY] = useState(0)
  useEffect(() => {
    const f = () => setY(Math.min(window.scrollY, 500) * 0.12)
    window.addEventListener('scroll', f, { passive: true })
    return () => window.removeEventListener('scroll', f)
  }, [])
  return (
    <section className="hero2">
      <div className="hero2-photo"><Photo {...shots.hero} /></div> 
      <div className="wrap hero2-in">
        <p className="eyebrow gold">KisanSathi</p>
        <h1>{t('heroTitle')}</h1>
        <p className="lead">{t('heroSub')}</p>
        <div className="cta">
          <Link to="/ask" className="btn btn-primary btn-lg">{t('ask')}</Link>
          <Link to="/schemes" className="btn btn-outline btn-lg">{t('exploreSchemes')}</Link>
        </div>
      </div>
    </section>
  )
}
