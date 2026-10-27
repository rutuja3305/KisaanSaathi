import { crops } from '../data/options.js'

export default function CropPicker({ value, onChange }) {
  const toggle = (c) => onChange(value.includes(c) ? value.filter((x) => x !== c) : [...value, c])
  return (
    <div className="chips" role="group" aria-label="Crops">
      {crops.map((c) => (
        <button type="button" key={c} className={`chip ${value.includes(c) ? 'on' : ''}`} aria-pressed={value.includes(c)} onClick={() => toggle(c)}>{c}</button>
      ))}
    </div>
  )
}
