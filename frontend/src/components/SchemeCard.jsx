import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { shots } from '../data/images.js'
import Photo from './Photo.jsx'

export default function SchemeCard({ scheme }) {
  const { t } = useApp()
  return (
    <article className="scheme hz">
      <div className="scheme-img"><Photo {...shots[scheme.shot || 's_state']} /></div>
      <div className="scheme-body">
        <span className="tag">{scheme.category}</span>
        <h3>{scheme.name}</h3>
        <p>{scheme.short}</p>
        <Link to={`/schemes/${scheme.id}`} className="btn btn-outline" aria-label={`${t('explore')} ${scheme.name}`}>{t('explore')} <ArrowRight size={16} /></Link>
      </div>
    </article>
  )
}
