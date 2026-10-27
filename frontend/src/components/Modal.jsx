import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'

export default function Modal({ title, onClose, children }) {
  const { t } = useApp()
  const ref = useRef(null)
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    ref.current?.focus()
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
  }, [onClose])
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={ref} onClick={(e) => e.stopPropagation()}>
        <button className="icon-btn modal-x" onClick={onClose} aria-label={t('close')}><X size={20} /> <span>{t('close')}</span></button>
        {children}
      </div>
    </div>
  )
}
