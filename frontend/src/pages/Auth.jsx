// Auth.jsx - full-screen login (mobile/email OTP - frontend demo only) + 4-step onboarding.
// Replace the fake OTP checks with real calls to your backend when ready.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, X } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { languages, irrigationTypes, ownershipTypes } from '../data/options.js'
import LocationFields from '../components/LocationFields.jsx'
import Photo from '../components/Photo.jsx'
import { shots } from '../data/images.js'
import CropPicker from '../components/CropPicker.jsx'

export default function Auth() {
  const { t, setUser, profile, updateProfile, lang, setLang } = useApp()
  const nav = useNavigate()
  const [phase, setPhase] = useState('id') // id -> otp -> onboard
  const [mode, setMode] = useState('mobile')
  const [id, setId] = useState('')
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [step, setStep] = useState(0)
  const steps = ['stepLocation', 'stepCrops', 'stepLang', 'stepFarm']
  const refs = [0, 1, 2, 3, 4, 5].map(() => null)

  const setDigit = (i, v) => {
    const d = v.replace(/\D/g, '').slice(-1); const n = [...otp]; n[i] = d; setOtp(n)
    if (d && i < 5) document.getElementById(`otp${i + 1}`)?.focus()
  }
  const finish = () => nav('/farm')
  const guest = () => { setUser({ guest: true }); nav('/farm') }

  return (
    <div className="auth">
      <div className="auth-art"><div className="cover"><Photo {...(phase === 'onboard' ? shots.loginWoman : shots.loginMan)} /></div><div className="hero-shade" /><div className="auth-quote"><h2>🌱 KisanSathi</h2><p>{t('tagline')}</p></div></div>
      <div className="auth-panel">
        <div className="auth-top">
          <button className="icon-btn" onClick={() => (phase === 'id' ? nav('/') : step > 0 && phase === 'onboard' ? setStep(step - 1) : setPhase('id'))}><ArrowLeft size={20} /> {t('back')}</button>
          <button className="icon-btn" onClick={() => nav('/')} aria-label={t('close')}><X size={20} /> {t('close')}</button>
        </div>

        {phase === 'id' && (
          <form onSubmit={(e) => { e.preventDefault(); if (id.trim()) setPhase('otp') }} className="auth-form">
            <h1>{t('login')}</h1>
            <div className="seg" role="group">
              <button type="button" className={mode === 'mobile' ? 'on' : ''} onClick={() => setMode('mobile')}>{t('mobile')}</button>
              <button type="button" className={mode === 'email' ? 'on' : ''} onClick={() => setMode('email')}>{t('email')}</button>
            </div>
            {mode === 'mobile'
              ? <div className="phone"><span>+91</span><input value={id} onChange={(e) => setId(e.target.value.replace(/\D/g, '').slice(0, 10))} placeholder="98765XXXXX" inputMode="numeric" aria-label={t('mobile')} autoFocus /></div>
              : <input className="full" type="email" value={id} onChange={(e) => setId(e.target.value)} placeholder="name@example.com" aria-label={t('email')} autoFocus />}
            <button className="btn btn-primary btn-lg block" type="submit" disabled={!id.trim()}>{t('sendOtp')}</button>
            <button type="button" className="btn btn-ghost block" onClick={guest}>{t('continueGuest')}</button>
          </form>
        )}

        {phase === 'otp' && (
          <form onSubmit={(e) => { e.preventDefault(); setUser({ guest: false }); updateProfile(mode === 'mobile' ? { mobile: id } : { email: id }); setPhase('onboard') }} className="auth-form">
            <h1>{t('enterOtp')}</h1>
            <p className="note">Demo: type any 6 digits.</p>
            <div className="otp">{otp.map((d, i) => <input key={i} id={`otp${i}`} value={d} onChange={(e) => setDigit(i, e.target.value)} inputMode="numeric" aria-label={`Digit ${i + 1}`} autoFocus={i === 0} />)}</div>
            <button className="btn btn-primary btn-lg block" type="submit" disabled={otp.some((d) => !d)}>{t('verify')}</button>
          </form>
        )}

        {phase === 'onboard' && (
          <div className="auth-form">
            <ol className="progress" aria-label="Progress">{steps.map((s, i) => <li key={s} className={i === step ? 'on' : i < step ? 'done' : ''}><b>0{i + 1}</b> {t(s)}</li>)}</ol>
            {step === 0 && <><h1>{t('whereFarm')}</h1><LocationFields value={profile} onChange={updateProfile} optional={false} /></>}
            {step === 1 && <><h1>{t('whatGrow')}</h1><CropPicker value={profile.crops} onChange={(crops) => updateProfile({ crops })} /></>}
            {step === 2 && <><h1>{t('whichLang')}</h1><div className="lang-big">{languages.map((l) => <button key={l.code} className={`chip big ${lang === l.code ? 'on' : ''}`} onClick={() => { setLang(l.code); updateProfile({ language: l.code }) }}>{l.label}</button>)}</div></>}
            {step === 3 && (
              <><h1>{t('tellMore')}</h1>
                <div className="fields">
                  <label>{t('name')}<input value={profile.name} onChange={(e) => updateProfile({ name: e.target.value })} /></label>
                  <label>{t('area')}<input value={profile.area} onChange={(e) => updateProfile({ area: e.target.value })} inputMode="decimal" /></label>
                  <label>{t('ownership')}<select value={profile.ownership} onChange={(e) => updateProfile({ ownership: e.target.value })}><option value="">-</option>{ownershipTypes.map((o) => <option key={o}>{o}</option>)}</select></label>
                  <label>{t('irrigation')}<select value={profile.irrigation} onChange={(e) => updateProfile({ irrigation: e.target.value })}><option value="">-</option>{irrigationTypes.map((o) => <option key={o}>{o}</option>)}</select></label>
                </div>
                <p className="note">{t('later712')}</p></>
            )}
            <div className="row">
              {step > 0 && <button className="btn btn-ghost" onClick={finish}>{t('skip')}</button>}
              <button className="btn btn-primary btn-lg" onClick={() => (step < 3 ? setStep(step + 1) : finish())}>{step < 3 ? t('next') : t('finish')}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
