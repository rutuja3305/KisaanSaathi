import { useEffect, useRef, useState } from 'react'
import { Send, Mic } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import SourceBadge from './SourceBadge.jsx'

const speechLang = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' }

export default function AIChat({ messages, loading, onSend }) {
  const { t, lang } = useApp()
  const [text, setText] = useState('')
  const [listening, setListening] = useState(false)
  const end = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const submit = (e) => { e.preventDefault(); if (!text.trim() || loading) return; onSend(text.trim()); setText('') }
  const voice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { alert('Voice input is not supported in this browser. Please type your question.'); return }
    const r = new SR(); r.lang = speechLang[lang]; setListening(true)
    r.onresult = (ev) => setText(ev.results[0][0].transcript)
    r.onend = () => setListening(false); r.onerror = () => setListening(false)
    r.start()
  }

  return (
    <div className="chat">
      <div className="chat-log" aria-live="polite">
        {messages.length === 0 && (
          <div className="chat-hello"><div className="bot" aria-hidden="true">🤖</div><h2>KisanSathi</h2><p>{t('askHello')}</p></div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <p>{m.text}</p>
            {m.sources?.map((s, j) => <SourceBadge key={j} source={s} />)}
          </div>
        ))}
        {loading && <div className="msg bot-msg"><span className="dots"><i /><i /><i /></span></div>}
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={submit}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t('askPlaceholder')} aria-label={t('askPlaceholder')} />
        <button type="button" className={`btn btn-ghost ${listening ? 'rec' : ''}`} onClick={voice}><Mic size={18} /> {t('voice')}</button>
        <button type="submit" className="btn btn-primary" disabled={!text.trim() || loading}><Send size={18} /> {t('send')}</button>
      </form>
    </div>
  )
}
