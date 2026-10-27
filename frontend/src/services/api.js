// services/api.js - the ONLY file that talks to your backend.
// If VITE_API_URL is empty, functions return demo data so the UI works standalone.
// Never put Supabase or Groq keys here. Those stay in your Python backend.
import { schemes } from '../data/schemes.js'

const BASE = import.meta.env.VITE_API_URL || ''
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

/**
 * Ask the RAG backend.
 * Sends:    { question, language, farmer_location, farmer_profile }
 * Expects:  { answer, language, sources: [{ title, organisation, page, url }], confidence }
 */
export async function askKisanSathi(question, language = 'en', farmer_location = {}, farmer_profile = {}) {
  if (BASE) return post('/api/ask', { question, language, farmer_location, farmer_profile })
  await wait(900)
  const q = question.toLowerCase()
  const demo = (answer, title, url) => ({
    answer, language, confidence: 'demo',
    sources: [{ title, organisation: 'Government of India', page: 10, url }]
  })
  if (q.includes('insur') || q.includes('pmfby') || q.includes('बीमा') || q.includes('विमा'))
    return demo('PMFBY is a crop insurance scheme. If your crop is damaged by a natural calamity, pest or disease, you can get compensation. You pay only a small part of the premium. Enrol through your bank, Common Service Centre or the PMFBY portal before the season cut-off date.', 'PMFBY Operational Guidelines', 'https://pmfby.gov.in')
  if (q.includes('loan') || q.includes('kcc') || q.includes('credit') || q.includes('कर्ज') || q.includes('ऋण'))
    return demo('A Kisan Credit Card gives you short-term credit for seeds, fertiliser and other farm needs. Visit your bank with ID, address and land or cultivation proof. Ask about interest support if you repay on time.', 'Kisan Credit Card Guidelines', 'https://www.myscheme.gov.in')
  if (q.includes('kisan') || q.includes('income') || q.includes('6000') || q.includes('scheme') || q.includes('योजना'))
    return demo('PM-KISAN gives eligible farmer families ₹6,000 a year in three instalments, sent directly to the bank account. Complete e-KYC to keep receiving instalments.', 'PM-KISAN Operational Guidelines', 'https://pmkisan.gov.in')
  return demo('This is a demo answer. Connect your Python RAG backend (see README) to get evidence-based answers from official documents.', 'Demo source', '')
}

export async function getSchemes(location = {}) {
  if (BASE) return post('/api/schemes', { location })
  await wait(100)
  const state = location.state
  return schemes.filter((s) => s.states === 'all' || (state && s.states.includes(state)))
}

export async function getFarmerProfile() {
  if (BASE) return (await fetch(`${BASE}/api/profile`)).json()
  return null // profile is kept in React context for now
}
export async function updateFarmerProfile(profile) {
  if (BASE) return post('/api/profile', profile)
  return profile
}
export async function uploadDocument(docId, file) {
  if (BASE) {
    const fd = new FormData(); fd.append('file', file); fd.append('doc_id', docId)
    const res = await fetch(`${BASE}/api/documents`, { method: 'POST', body: fd })
    return res.json()
  }
  await wait(400)
  return { id: docId, name: file.name, status: 'added' }
}
