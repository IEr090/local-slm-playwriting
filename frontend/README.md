# Anton: Character Creator (frontend)

Web frontend for the Character Creator: premise → generated cast → character editing.
Vite + React + TypeScript + Tailwind + shadcn/ui + Motion. All data comes from a mock `api`
(`src/features/characters/api`), no backend is needed yet.

## Requirements

- Node.js 20 or newer (`node -v`)

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | dev server with hot reload |
| `npm run build` | type check + production build to `dist/` |
| `npm run preview` | serve the production build |
| `npm test` | unit tests (Vitest) |
| `npm run lint` | lint (oxlint) |

## Pages

| URL | Page |
|---|---|
| `/` | premise prompt |
| `/generating` | generation animation (only while generating, otherwise back to `/`) |
| `/cast` | cast grid "Dramatis Personae" |
| `/cast/:id` | character detail; leaving it (button, browser Back, any link) auto-saves |

The mock api keeps the saved cast in `localStorage` (`anton.mock-cast.v1`), so `/cast` and
`/cast/:id` survive a reload. Clear it to start fresh. When hosting the build, serve `index.html`
for every path (SPA fallback); `npm run dev` and `npm run preview` already do.

## Mock api switches

Add to the URL to test states without a model:

| Parameter | Effect |
|---|---|
| `?genDelay=1500` | cast generation takes 1500 ms instead of 4500 ms |
| `?fail=generate` | cast generation fails (error banner) |
| `?fail=card` | card update after editing fails, old card is kept |
| `?fail=chat` | "Ask AI to revise" fails |

Several can be combined: `?genDelay=300&fail=card,chat`.

## Structure

```
src/
  app/                    App (routes + page transitions + error banner), Providers
  shared/                 used by every feature
    api/errors.ts         ApiError, ApiErrorInfo, toErrorInfo
    errors/               ErrorsProvider, useErrors (the banner's error)
    ui/                   Pill, Chip, Orb, Toast, ErrorBanner, icons
    ui/shadcn/            generated shadcn/ui components
    lib/  hooks/          cn(), useAutoGrow
  features/
    characters/           Character Creator
      api/                mock api, the only data source
      model/              types, labels, pure helpers (+ tests)
      store/              reducer, context, CastProvider
      pages/              prompt, generating, grid, detail
      paths.ts routes.tsx URLs and the route table
```

A new feature (e.g. plot) gets its own `features/<name>/` with the same folders, adds its
routes in `app/App.tsx` and its provider in `app/Providers.tsx`.

Fonts are bundled via `@fontsource`, so the app works offline.
