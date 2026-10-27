// SourceBadge - farmer-friendly source label. Page numbers are hidden inside "View source details".
import { useState } from 'react'
import { ShieldCheck, ChevronDown } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'

export default function SourceBadge({ source }) {
  const { t } = useApp()
  const [open, setOpen] = useState(false)
  return (
    <div className="source">
      <div className="source-top"><ShieldCheck size={16} /> <strong>{t('official')}</strong> · {source.title}</div>
      <button className="link-btn" onClick={() => setOpen(!open)} aria-expanded={open}>{t('viewDetails')} <ChevronDown size={14} className={open ? 'flip' : ''} /></button>
      {open && (
        <dl className="source-details">
          <dt>Organisation</dt><dd>{source.organisation}</dd>
          <dt>Document</dt><dd>{source.title}</dd>
          {source.page != null && <><dt>Page</dt><dd>{source.page}</dd></>}
          {source.url && <><dt>Link</dt><dd><a href={source.url} target="_blank" rel="noreferrer">{source.url}</a></dd></>}
        </dl>
      )}
    </div>
  )
}
