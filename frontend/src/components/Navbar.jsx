// Navbar.jsx - top navigation (desktop) + bottom navigation (mobile). Edit `links` to change navigation.
import { Link, NavLink } from 'react-router-dom'
import { Home, Sprout, Landmark, FileText, MessageCircle, User } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import LanguageSelector from './LanguageSelector.jsx'

const links = [
  { to: '/', key: 'home', icon: Home, end: true },
  { to: '/farm', key: 'farm', icon: Sprout },
  { to: '/schemes', key: 'schemes', icon: Landmark },
  { to: '/documents', key: 'documents', icon: FileText },
  { to: '/ask', key: 'ask', icon: MessageCircle }
]

export default function Navbar() {
  const { t, user, profile } = useApp()
  return (
    <>
      <header className="nav">
        <div className="nav-in">
          <Link to="/" className="logo" aria-label="KisanSathi home"><span aria-hidden="true">🌱</span> KisanSathi</Link>
          <nav className="nav-links" aria-label="Main">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? 'active' : '')}>{t(l.key)}</NavLink>
            ))}
          </nav>
          <div className="nav-right">
            <LanguageSelector />
            {user ? (
              <Link to="/profile" className="btn btn-ghost"><User size={18} /> {profile.name || t('profile')}</Link>
            ) : (
              <Link to="/auth" className="btn btn-primary">{t('login')}</Link>
            )}
          </div>
        </div>
      </header>
      <nav className="bottom-nav" aria-label="Main mobile">
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? 'active' : '')}>
            <l.icon size={22} /><span>{l.key === 'ask' ? 'Ask' : t(l.key)}</span>
          </NavLink>
        ))}
      </nav>
    </>
  )
}
