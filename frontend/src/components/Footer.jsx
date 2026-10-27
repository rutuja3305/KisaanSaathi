import { Link } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'

export default function Footer() {
  const { t } = useApp()
  return (
    <footer className="footer">
      <div className="wrap footer-in">
        <div><strong>🌱 KisanSathi</strong><p>{t('tagline')}</p></div>
        <nav aria-label="Footer">
          <Link to="/schemes">{t('schemes')}</Link>
          <Link to="/documents">{t('documents')}</Link>
          <Link to="/ask">{t('ask')}</Link>
        </nav>
      </div>
    </footer>
  )
}
