import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, MessageCircle } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { schemes } from '../data/schemes.js'

export default function SchemeDetail() {
  const { id } = useParams()
  const { t } = useApp()
  const nav = useNavigate()
  const s = schemes.find((x) => x.id === id)
  if (!s) return <div className="wrap pagepad"><Link to="/schemes" className="btn btn-ghost"><ArrowLeft size={16} /> {t('back')}</Link><p>Scheme not found.</p></div>
  return (
    <div className="wrap pagepad narrow">
      <button className="btn btn-ghost" onClick={() => nav(-1)}><ArrowLeft size={16} /> {t('back')}</button>
      <span className="tag">{s.category}</span>
      <h1 className="h1">{s.name}</h1>
      <p className="lead-dark">{s.about}</p>
      <h3>{t('eligibility')}</h3>
      <ul className="ticks">{s.eligibility.map((x) => <li key={x}>{x}</li>)}</ul>
      <h3>{t('howApply')}</h3>
      <ol className="ticks num">{s.apply.map((x) => <li key={x}>{x}</li>)}</ol>
      <p className="note">{t('official')}: {s.source}</p>
      <div className="cta dark">
        <Link to={`/ask?q=${encodeURIComponent('Tell me about ' + s.name)}`} className="btn btn-primary btn-lg"><MessageCircle size={18} /> {t('askAbout')}</Link>
        <a href={s.link} target="_blank" rel="noreferrer" className="btn btn-outline btn-lg">{t('officialSite')} <ExternalLink size={16} /></a>
      </div>
    </div>
  )
}
