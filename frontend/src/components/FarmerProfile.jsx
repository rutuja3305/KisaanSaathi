import { useState } from 'react'
import { useApp } from '../context/AppContext.jsx'
import { irrigationTypes, ownershipTypes, languages } from '../data/options.js'
import { updateFarmerProfile } from '../services/api.js'
import LocationFields from './LocationFields.jsx'
import CropPicker from './CropPicker.jsx'

export default function FarmerProfile() {
  const { t, profile, updateProfile, setLang } = useApp()
  const [saved, setSaved] = useState(false)
  const set = (patch) => { updateProfile(patch); setSaved(false) }
  const save = async (e) => { e.preventDefault(); await updateFarmerProfile(profile); setSaved(true) }
  return (
    <form className="form" onSubmit={save}>
      <div className="fields">
        <label>{t('name')}<input value={profile.name} onChange={(e) => set({ name: e.target.value })} autoComplete="name" /></label>
        <label>{t('mobile')}<input value={profile.mobile} onChange={(e) => set({ mobile: e.target.value })} inputMode="numeric" autoComplete="tel" /></label>
        <label>{t('email')}<input type="email" value={profile.email} onChange={(e) => set({ email: e.target.value })} autoComplete="email" /></label>
        <label>Language
          <select value={profile.language} onChange={(e) => { set({ language: e.target.value }); setLang(e.target.value) }}>
            {languages.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </label>
      </div>
      <h3>{t('tellWhere')}</h3>
      <LocationFields value={profile} onChange={set} />
      <h3>{t('farm')}</h3>
      <div className="fields">
        <label>{t('ownership')}
          <select value={profile.ownership} onChange={(e) => set({ ownership: e.target.value })}><option value="">-</option>{ownershipTypes.map((o) => <option key={o}>{o}</option>)}</select>
        </label>
        <label>{t('area')}<input value={profile.area} onChange={(e) => set({ area: e.target.value })} inputMode="decimal" /></label>
        <label>{t('irrigation')}
          <select value={profile.irrigation} onChange={(e) => set({ irrigation: e.target.value })}><option value="">-</option>{irrigationTypes.map((o) => <option key={o}>{o}</option>)}</select>
        </label>
      </div>
      <p className="label">{t('myCrops')}</p>
      <CropPicker value={profile.crops} onChange={(crops) => set({ crops })} />
      <p className="note">{t('later712')}</p>
      <button className="btn btn-primary btn-lg" type="submit">{saved ? '✓ ' + t('saved') : t('save')}</button>
    </form>
  )
}
