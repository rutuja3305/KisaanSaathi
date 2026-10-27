import { Link } from 'react-router-dom'
import { Check, Sprout, ShieldCheck } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { shots } from '../data/images.js'
import Photo from './Photo.jsx'

// Photo of a farmer with a clean KisanSathi chat card on top. The one place on Home that introduces the AI.
export default function AIShowcase() {
  const { t } = useApp()
  return (
    <div className="ai-grid">
      <div>
        <p className="eyebrow dark">{t('onePlace')}</p>
        <h2>{t('askTitle')}</h2>
        <p className="sub">{t('askSub')}</p>
        <ul className="ai-points">
          {['onePlace1', 'onePlace2', 'onePlace3', 'onePlace4'].map((k) => <li key={k}><Check size={18} /> {t(k)}</li>)}
        </ul>
        <Link to="/ask" className="btn btn-primary btn-lg">{t('ask')}</Link>
      </div>
      <div className="ai-visual hz">
        <div className="ai-photo"><Photo {...shots.aiFarmer} /></div>
        <div className="ai-ui">
          <div className="ai-q">{t('demoQ')}</div>
          <p className="ai-a"><Sprout size={18} /> {t('demoA')}</p>
          <div className="ai-cards">
            <Link to="/schemes/pm-kisan"><b>PM-KISAN</b><small>Income support</small></Link>
            <Link to="/schemes/pmfby"><b>PMFBY</b><small>Crop insurance</small></Link>
          </div>
          <div className="ai-src"><ShieldCheck size={14} /> {t('official')}</div>
        </div>
      </div>
    </div>
  )
}
