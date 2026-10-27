import { Brain, Plane, Satellite, Target, Droplets, Radio } from 'lucide-react'

export const technologies = [
  { id: 'ai', shot: 't_ai',  icon: Brain, title: 'AI-powered agriculture', short: 'Understand information and decide better.',
    detail: 'AI can read long official documents and explain them in simple language, helping farmers understand schemes, insurance and loans without the paperwork.' },
  { id: 'drone', shot: 't_drone',  icon: Plane, title: 'Drone technology', short: 'A bird’s-eye view of the field.',
    detail: 'Drones can support crop monitoring, spraying and field assessment, saving time and reducing the effort of walking large fields.' },
  { id: 'satellite', shot: 't_satellite',  icon: Satellite, title: 'Satellite & remote sensing', short: 'Watch large areas from space.',
    detail: 'Satellite imagery is used for large-scale crop and field monitoring, helping spot stress or damage across wide areas.' },
  { id: 'precision', shot: 't_precision',  icon: Target, title: 'Precision agriculture', short: 'The right input, in the right place.',
    detail: 'Using field data to decide how much seed, fertiliser and water each part of the field really needs, reducing waste.' },
  { id: 'irrigation', shot: 't_irrigation',  icon: Droplets, title: 'Smart irrigation', short: 'Water only when the crop needs it.',
    detail: 'Sensors and automated systems can help manage water more efficiently, especially where water is scarce.' },
  { id: 'iot', shot: 't_iot',  icon: Radio, title: 'IoT & farm sensors', short: 'Your soil, talking to you.',
    detail: 'Connected sensors can provide information about soil, moisture and field conditions so problems are noticed early.' }
]
