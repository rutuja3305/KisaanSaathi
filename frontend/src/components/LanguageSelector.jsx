import { useApp } from '../context/AppContext.jsx'
import { languages } from '../data/options.js'

export default function LanguageSelector() {
  const { lang, setLang, updateProfile } = useApp()
  return (
    <div className="lang" role="group" aria-label="Language">
      {languages.map((l) => (
        <button key={l.code} className={lang === l.code ? 'on' : ''} aria-pressed={lang === l.code}
          onClick={() => { setLang(l.code); updateProfile({ language: l.code }) }}>{l.label}</button>
      ))}
    </div>
  )
}
