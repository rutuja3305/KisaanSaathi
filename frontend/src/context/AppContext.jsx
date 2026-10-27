// Global state: UI language, logged-in user, farmer profile, documents.
import { createContext, useContext, useState, useCallback } from 'react'
import { translations } from '../data/translations.js'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

const defaultProfile = {
  name: '', mobile: '', email: '', state: 'Maharashtra', district: 'Pune',
  taluka: '', village: '', language: 'en',
  ownership: '', area: '', crops: [], irrigation: '', survey712: ''
}
const defaultDocs = [
  { id: 'd712', level: 'recommended', key: 'doc712', status: 'missing', file: '' },
  { id: 'id', level: 'required', key: 'docId', status: 'missing', file: '' },
  { id: 'bank', level: 'required', key: 'docBank', status: 'missing', file: '' },
  { id: 'land', level: 'recommended', key: 'docLand', status: 'missing', file: '' },
  { id: 'other', level: 'optional', key: 'docOther', status: 'missing', file: '' }
]

export function AppProvider({ children }) {
  const [lang, setLang] = useState('en')
  const [user, setUser] = useState(null) // null | { guest: bool }
  const [profile, setProfile] = useState(defaultProfile)
  const [docs, setDocs] = useState(defaultDocs)

  const t = useCallback((key) => translations[lang]?.[key] ?? translations.en[key] ?? key, [lang])
  const updateProfile = (patch) => setProfile((p) => ({ ...p, ...patch }))
  const updateDoc = (id, patch) => setDocs((d) => d.map((x) => (x.id === id ? { ...x, ...patch } : x)))

  return (
    <Ctx.Provider value={{ lang, setLang, t, user, setUser, profile, updateProfile, docs, updateDoc }}>
      {children}
    </Ctx.Provider>
  )
}
