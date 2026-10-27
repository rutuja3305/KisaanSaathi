import { useState } from 'react'
import { useApp } from '../context/AppContext.jsx'
import { technologies } from '../data/technologies.js'
import { shots } from '../data/images.js'
import Photo from './Photo.jsx'
import Modal from './Modal.jsx'
import Reveal from './Reveal.jsx'

// Six small horizontal cards. Hover reveals more; click opens the detail popup.
export default function TechnologySection() {
  const { t } = useApp()
  const [open, setOpen] = useState(null)
  return (
    <section className="section">
      <div className="wrap"><Reveal>
        <h2>{t('changing')}</h2>
        <p className="sub">{t('changingSub')}</p>
        <div className="tech3-grid">
          {technologies.map((x) => (
            <button key={x.id} className="tcard hz" onClick={() => setOpen(x)}>
              <div className="tcard-img"><Photo {...shots[x.shot]} /></div>
              <div className="tcard-body">
                <x.icon size={22} />
                <strong>{x.title}</strong>
                <small>{x.short}</small>
                <p className="tcard-more">{x.detail}</p>
              </div>
            </button>
          ))}
        </div>
      </Reveal></div>
      {open && (
        <Modal title={open.title} onClose={() => setOpen(null)}>
          <div className="modal-photo hz"><Photo {...shots[open.shot]} /></div>
          <h3>{open.title}</h3>
          <p>{open.detail}</p>
        </Modal>
      )}
    </section>
  )
}
