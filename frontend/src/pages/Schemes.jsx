import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext.jsx'
import { getSchemes } from '../services/api.js'
import { categories } from '../data/schemes.js'
import SchemeCard from '../components/SchemeCard.jsx'

export default function Schemes() {
  const { t, profile } = useApp()
  const [list, setList] = useState([])
  const [cat, setCat] = useState('all')
  useEffect(() => { getSchemes({ state: profile.state, district: profile.district }).then(setList) }, [profile.state, profile.district])
  const shown = cat === 'all' ? list : list.filter((s) => s.category === cat)
  return (
    <div className="wrap pagepad">
      <h1 className="h1">{t('schemes')}</h1>
      <p className="sub">{profile.district}, {profile.state}</p>
      <div className="chips" role="group" aria-label="Category">
        {['all', ...categories].map((c) => <button key={c} className={`chip ${cat === c ? 'on' : ''}`} aria-pressed={cat === c} onClick={() => setCat(c)}>{c === 'all' ? t('all') : c}</button>)}
      </div>
      <div className="scheme-grid">{shown.map((s) => <SchemeCard key={s.id} scheme={s} />)}</div>
    </div>
  )
}
