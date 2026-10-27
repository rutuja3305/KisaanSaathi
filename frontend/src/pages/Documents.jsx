import { useApp } from '../context/AppContext.jsx'
import DocumentCard from '../components/DocumentCard.jsx'

// No photographs here on purpose: clean cards only.
export default function Documents() {
  const { t, docs } = useApp()
  return (
    <div className="wrap pagepad">
      <h1 className="h1">{t('myDocuments')}</h1>
      <p className="sub">{t('later712')}</p>
      <div className="doc-grid">{docs.map((d) => <DocumentCard key={d.id} doc={d} />)}</div>
      <p className="note">{t('docNote')}</p>
    </div>
  )
}
