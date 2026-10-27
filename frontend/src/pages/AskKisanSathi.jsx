import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Sprout, Landmark, ShieldCheck, Banknote, FileText, MapPin } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { askKisanSathi } from '../services/api.js'
import AIChat from '../components/AIChat.jsx'
import Photo from '../components/Photo.jsx'
import { shots } from '../data/images.js'

export default function AskKisanSathi() {
  const { t, lang, profile } = useApp()
  const [params] = useSearchParams()
  const [messages, setMessages] = useState([])
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(false)
  const started = useRef(false)

  const send = async (q) => {
    setMessages((m) => [...m, { role: 'user', text: q }])
    setRecent((r) => [q, ...r.filter((x) => x !== q)].slice(0, 6))
    setLoading(true)
    try {
      const res = await askKisanSathi(q, lang, { state: profile.state, district: profile.district, taluka: profile.taluka, village: profile.village }, profile)
      setMessages((m) => [...m, { role: 'bot-msg', text: res.answer, sources: res.sources }])
    } catch {
      setMessages((m) => [...m, { role: 'bot-msg', text: 'Sorry, something went wrong. Please try again.' }])
    }
    setLoading(false)
  }
  useEffect(() => { const q = params.get('q'); if (q && !started.current) { started.current = true; send(q) } }, []) // eslint-disable-line

  const topics = [
    [Sprout, 'qCrops', `Which schemes help ${profile.crops[0] || 'my'} crops?`], [Landmark, 'qSchemes', 'Which government schemes can I get?'],
    [ShieldCheck, 'qInsurance', 'How does crop insurance work?'], [Banknote, 'qLoans', 'How do I get a Kisan Credit Card loan?'],
    [FileText, 'qDocs', 'Which documents do I need for PM-KISAN?'], [MapPin, 'qNear', `Where can I get help in ${profile.district}?`]
  ]
  return (
    <div className="ask">
      <aside className="ask-side">
        <h2>{t('recent')}</h2>
        {recent.length === 0 ? <p className="note">{t('noRecent')}</p> : <ul>{recent.map((r) => <li key={r}><button onClick={() => send(r)}>{r}</button></li>)}</ul>}
        <h2>{t('quickTopics')}</h2>
        <ul>{topics.map(([Icon, k, q]) => <li key={k}><button onClick={() => send(q)}><Icon size={16} /> {t(k)}</button></li>)}</ul>
      </aside>
      <section className="ask-main">
        <div className="ask-bg"><Photo {...shots.ask_bg} /></div>
        {messages.length === 0 && (
          <div className="quick">{topics.map(([Icon, k, q]) => <button key={k} className="quick-btn" onClick={() => send(q)}><Icon size={20} /> {t(k)}</button>)}</div>
        )}
        <AIChat messages={messages} loading={loading} onSend={send} />
      </section>
    </div>
  )
}
