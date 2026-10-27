import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import FarmerProfile from '../components/FarmerProfile.jsx'

export default function Profile() {
  const { t, user, setUser } = useApp()
  const nav = useNavigate()
  return (
    <div className="wrap pagepad narrow">
      <h1 className="h1">{t('profile')}</h1>
      <FarmerProfile />
      {user ? <button className="btn btn-ghost" onClick={() => { setUser(null); nav('/') }}>{t('logout')}</button>
        : <button className="btn btn-primary" onClick={() => nav('/auth')}>{t('login')}</button>}
    </div>
  )
}
