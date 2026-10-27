import { useApp } from '../context/AppContext.jsx'
import { locations } from '../data/options.js'

// State + District are the key location fields. Taluka / village are optional.
export default function LocationFields({ value, onChange, optional = true }) {
  const { t } = useApp()
  const districts = locations[value.state] || []
  return (
    <div className="fields">
      <label>{t('state')}
        <select value={value.state} onChange={(e) => onChange({ state: e.target.value, district: locations[e.target.value][0] })}>
          {Object.keys(locations).map((s) => <option key={s}>{s}</option>)}
        </select>
      </label>
      <label>{t('district')}
        <select value={value.district} onChange={(e) => onChange({ district: e.target.value })}>
          {districts.map((d) => <option key={d}>{d}</option>)}
        </select>
      </label>
      {optional && (
        <>
          <label>{t('taluka')}<input value={value.taluka || ''} onChange={(e) => onChange({ taluka: e.target.value })} /></label>
          <label>{t('village')}<input value={value.village || ''} onChange={(e) => onChange({ village: e.target.value })} /></label>
        </>
      )}
    </div>
  )
}
