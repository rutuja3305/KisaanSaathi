// Photo - shows one "shot" from data/images.js. Usage: <Photo {...shots.sunrise} />
export default function Photo({ src, pos = '50% 50%', zoom = 1, className = '' }) {
  return <img src={src} alt="" className={`photo ${className}`} style={{ objectPosition: pos, transformOrigin: pos, '--z': zoom }} />
}
