import Photo from './Photo.jsx'
import { shots } from '../data/images.js'

// light = calm off-white header with a soft photo on the right (used on My Farm)
export default function PageBanner({ shot = 'banner_farm', light = false, children }) {
  return (
    <section className={`banner ${light ? 'light' : ''}`}>
      <div className="banner-bg"><Photo {...shots[shot]} /></div>
      <div className="banner-shade" />
      <div className="wrap banner-in">{children}</div>
    </section>
  )
}
