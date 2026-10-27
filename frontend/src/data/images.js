// images.js - every photo on the site is configured here.
// shot = { src: photo file, pos: focus point (CSS object-position), zoom: 1 = none }
const img = (file, pos = '50% 50%', zoom = 1) => ({ src: `/images/${file}`, pos, zoom })

export const shots = {
  // hero + login/onboarding
  hero: img('hero-woman.jpg', '60% 25%', 1),
  loginMan: img('man-phone.jpg', '50% 10%'),
  loginWoman: img('hero-woman.jpg', '62% 40%', 1.1),
  // technology cards
  t_ai: img('hero.jpg', '28% 72%', 1.5),
  t_drone: img('drone-didi.jpg', '12% 35%', 1.3),
  t_satellite: img('aerial-fields.jpg'),
  t_precision: img('sprayer.jpg', '50% 55%'),
  t_irrigation: img('aerial-canal.jpg', '30% 50%', 1.1),
  t_iot: img('sensor-station.jpg', '30% 40%', 1.1),
  // AI showcase, location, trust
  aiFarmer: img('woman-tablet.jpg', '50% 35%'),
  maharashtra: img('maharashtra.jpg', '50% 62%', 1.1),
  docs: img('man-documents.jpg', '50% 30%'),
  // scheme cards
  s_pmkisan: img('man-phone.jpg', '60% 35%', 1.5),
  s_pmfby: img('rice-closeup.jpg', '50% 60%'),
  s_mahadbt: img('smart-farm.jpg', '8% 60%', 1.4),
  s_kcc: img('drone-didi.jpg', '65% 45%', 1.4),
  s_state: img('hero.jpg', '78% 35%', 1.5),
  // page backgrounds
  banner_farm: img('aerial-fields.jpg', '50% 60%'),
  ask_bg: img('rice-closeup.jpg')
}
