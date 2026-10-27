import { useRef } from 'react'
import { FileText, Upload, Eye, CheckCircle2 } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { uploadDocument } from '../services/api.js'

export default function DocumentCard({ doc }) {
  const { t, updateDoc } = useApp()
  const input = useRef(null)
  const added = doc.status === 'added'
  const pick = async (e) => {
    const f = e.target.files?.[0]; if (!f) return
    await uploadDocument(doc.id, f)
    updateDoc(doc.id, { status: 'added', file: f.name })
  }
  return (
    <article className={`doc ${added ? 'added' : ''}`}>
      <span className={`lvl lvl-${doc.level}`}>{t(doc.level === 'required' ? 'req' : doc.level === 'recommended' ? 'rec' : 'opt')}</span>
      <FileText size={26} />
      <h3>{t(doc.key)}</h3>
      <p className="status">{added ? <><CheckCircle2 size={16} /> {doc.file}</> : t('status_missing')}</p>
      <input ref={input} type="file" hidden onChange={pick} aria-label={`${t('upload')} ${t(doc.key)}`} />
      {added
        ? <button className="btn btn-outline" onClick={() => alert(`${doc.file}\n\n${t('docNote')}`)}><Eye size={16} /> {t('view')}</button>
        : <button className="btn btn-primary" onClick={() => input.current.click()}><Upload size={16} /> {t('upload')}</button>}
    </article>
  )
}
