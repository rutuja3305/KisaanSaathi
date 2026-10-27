import { Link } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { shots } from '../data/images.js'
import Photo from './Photo.jsx'
import LocationFields from './LocationFields.jsx'

// State > District > Taluka > Village. Editing here updates the farmer profile used everywhere else.
export default function LocationSection() {
  const { t, profile, updateProfile } = useApp()
  const steps = [['state', profile.state], ['district', profile.district], ['taluka', profile.taluka], ['village', profile.village]]
  return (
    <div className="loc-grid">
      <div className="loc-photo hz">
        <Photo {...shots.maharashtra} />
        <svg className="contours" viewBox="0 0 400 500" preserveAspectRatio="none" aria-hidden="true">
          <path d="M-10 380 C90 330 160 400 260 340 S380 300 420 330" /><path d="M-10 420 C100 370 170 450 270 385 S390 345 420 375" /><path d="M-10 460 C110 410 180 490 280 430 S400 390 420 420" />
        </svg>
        <span className="loc-pill"><MapPin size={16} /> {profile.district}, {profile.state}</span>
      </div>
      <div>
        <h2>{t('tellWhere')}</h2>
        <p className="sub">{t('locSub')}</p>
        <ol className="loc-path">
          {steps.map(([k, v], i) => <li key={k} className={v ? 'on' : ''}><span className="dot" /><em>{t(k)}</em>{v && <strong>{v}</strong>}</li>)}
        </ol>
        <LocationFields value={profile} onChange={updateProfile} optional={false} />
        <Link to="/schemes" className="btn btn-primary">{t('showLoc')}</Link>
      </div>
    </div>
  )
}
