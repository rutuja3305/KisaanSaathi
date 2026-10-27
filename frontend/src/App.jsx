// App.jsx - ALL ROUTES live here. Add a new page = add a <Route>.
import { useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import Home from './pages/Home.jsx'
import MyFarm from './pages/MyFarm.jsx'
import Schemes from './pages/Schemes.jsx'
import SchemeDetail from './pages/SchemeDetail.jsx'
import AskKisanSathi from './pages/AskKisanSathi.jsx'
import Documents from './pages/Documents.jsx'
import Profile from './pages/Profile.jsx'
import Auth from './pages/Auth.jsx'

export default function App() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  const fullscreen = pathname === '/auth'
  return (
    <>
      <a href="#main" className="skip">Skip to content</a>
      {!fullscreen && <Navbar />}
      <main id="main" key={pathname} className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/farm" element={<MyFarm />} />
          <Route path="/schemes" element={<Schemes />} />
          <Route path="/schemes/:id" element={<SchemeDetail />} />
          <Route path="/ask" element={<AskKisanSathi />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      {!fullscreen && pathname !== '/ask' && <Footer />}
    </>
  )
}
