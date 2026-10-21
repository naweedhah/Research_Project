# Frontend

One web app for the integrated system: an **Overview** page summarising all four components, then a section per
component. Built with Vite, React 19, React Router 7 and Tailwind CSS 4. It talks only to the backend API.

## Run

```bash
cd frontend
npm install
cp .env.example .env.local        # API address (default http://localhost:8000) and C1's clinical app address
npm run dev                       # http://localhost:5173
```

Start the backend first (see the root README). Create an account on the sign-in page (shared `/auth` routes).
`npm run build` produces `dist/` (not committed).

## Pages

| Section | Pages | Backend |
|---|---|---|
| Overview | live card per component, how they connect, what needs attention | every `/status` + C4 warnings |
| C1 Risk assessment | model, outputs and triage; link to C1's clinical app | `/risk` |
| C2 Interventions | child form, feasibility checks, ranked intervention cards | `/interventions/recommendations` |
| C3 Model reliability | Model health (demo cycles), Live monitoring, Versions & approvals, Experiment results | `/maintenance` |
| C4 Burden forecasting | Dashboard, Forecast, GIS map, Resources, Early warning, Trends, Explainable AI, District details | `/forecast` |

## Structure and ownership

```
src/
  config/components.js     the four components: names, colours, icons, status endpoints (shared)
  routes/c1.jsx … c4.jsx   each component's routes and sidebar entries: edit only your own file
  pages/home/              Overview (shared)
  pages/c1/ c2/ c3/        Components 1–3
  pages/component4/        Component 4 (Nimshara's pages), with components/component4/, services/component4/,
                           context/Component4SelectionContext.jsx
  ui/                      shared cards, badges, buttons, states
  layout/AppShell.jsx      sidebar and top bar (shared)
  index.css                theme tokens
```

Work inside your own route file and page folder. Shared files (`App.jsx`, `layout/`, `ui/`, `config/`, `index.css`)
change only by agreement.

## Theme

Tokens in `src/index.css`: `primary` (ink #0f2a3d), `secondary` (brand teal #0e7c7b), `surface`, `line`, `muted`,
`success`, `warning`, `danger`, plus one identity colour per component — `c1` blue, `c2` green, `c3` violet,
`c4` amber — used for its sidebar group, page header and overview card. Font: Inter (bundled, works offline).
The GIS map's background tiles come from OpenStreetMap and need internet; district shapes draw without it.
