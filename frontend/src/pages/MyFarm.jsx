import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapPin, Pencil, Sprout } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { getSchemes } from '../services/api.js'
import { seasonOf } from '../data/options.js'
import SchemeCard from '../components/SchemeCard.jsx'
import DocumentCard from '../components/DocumentCard.jsx'
import PageBanner from '../components/PageBanner.jsx'

export default function MyFarm() {
  const { t, profile, docs, user } = useApp()
  const [list, setList] = useState([])
  useEffect(() => { getSchemes({ state: profile.state, district: profile.district }).then(setList) }, [profile.state, profile.district])
  return (
    <>
    <PageBanner shot="banner_farm" light>
      <div className="farm-head">
        <div>
          <h1 className="h1">{t('namaste')}, {profile.name || (user?.guest === false ? '' : 'Kisan')}</h1>
          <p className="sub">{t('relevantSub')}</p>
          <p className="loc"><MapPin size={18} /> {[profile.village, profile.taluka, profile.district, profile.state].filter(Boolean).join(', ')}
            {profile.area && <> · {profile.area} acres</>}{profile.irrigation && <> · {profile.irrigation}</>}</p>
        </div>
        <Link to="/profile" className="btn btn-outline"><Pencil size={16} /> {t('farmProfile')}: {t('edit')}</Link>
      </div>
    </PageBanner>
    <div className="wrap pagepad">
      <h2 className="h2">{t('myCrops')}</h2>
      {profile.crops.length === 0
        ? <p className="empty">No crops added yet. <Link to="/profile">{t('edit')}</Link></p>
        : <div className="crop-grid">{profile.crops.map((c) => (
            <div key={c} className="crop"><Sprout size={22} /><h3>{c}</h3><p>{seasonOf[c] || ''}</p><span className="tag">Growing</span></div>
          ))}</div>}

      <h2 className="h2">{t('recommended')}</h2>
      <div className="scheme-grid">{list.slice(0, 4).map((s) => <SchemeCard key={s.id} scheme={s} />)}</div>

      <h2 className="h2">{t('myDocuments')}</h2>
      <div className="doc-grid">{docs.slice(0, 4).map((d) => <DocumentCard key={d.id} doc={d} />)}</div>
      <p className="note">{t('later712')}</p>
    </div>
    </>
  )
}
