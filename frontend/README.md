# KisanSathi Frontend (React + Vite)

## Install & run
```bash
npm install
npm run dev      # opens http://localhost:5173
npm run build    # production build
```

## Folder structure
```
src/
  main.jsx            entry
  App.jsx             ALL ROUTES (navigation)
  context/AppContext  language, user, profile, documents (global state)
  components/         Navbar, Hero, TechnologySection, SchemeCard, AIChat, SourceBadge, DocumentCard, ...
  pages/              Home, MyFarm, Schemes, SchemeDetail, AskKisanSathi, Documents, Profile, Auth (login + onboarding)
  data/               translations.js, schemes.js, technologies.js, options.js
  services/api.js     ALL backend calls
  styles/index.css    all styling and colour tokens
```

## Where things are controlled
- **Navigation:** `src/App.jsx` (routes) and `src/components/Navbar.jsx` (menu links, also mobile bottom bar)
- **Translations:** `src/data/translations.js` (en / mr / hi). Use `t('key')` in components.
- **API integration:** `src/services/api.js`

## Connecting your RAG backend
1. Copy `.env.example` to `.env` and set `VITE_API_URL=http://localhost:8000` (your Python API).
2. Expose these endpoints from Python (FastAPI/Flask). Keep Supabase and Groq keys ONLY there:
   - `POST /api/ask` receives `{question, language, farmer_location, farmer_profile}` and returns `{answer, language, sources:[{title, organisation, page, url}], confidence}`
   - `POST /api/schemes`, `GET/POST /api/profile`, `POST /api/documents` (optional for now)
3. Enable CORS in the backend for `http://localhost:5173`, or use the Vite proxy in `vite.config.js`.

When `VITE_API_URL` is empty the app uses demo answers, so the UI works without the backend.

## Notes
- Page numbers are hidden under "View source details" in each answer.
- Images are illustrated SVG scenes (`components/Landscape.jsx`); swap in real photos later if you like.
- Login/OTP and document upload are frontend demos only.

## Photos
All photos are defined in `src/data/images.js`. Drop new images into `public/images/`, add them to `IMG`, and
point any "shot" at them (choose focus point + zoom). Use 1920px+ photos for the sharpest full-width backgrounds.
