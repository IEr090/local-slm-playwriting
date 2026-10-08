# Anton: Character Creator (frontend)

Web frontend for the Character Creator: premise → generated cast → character editing.
Vite + React + TypeScript + Tailwind + shadcn/ui + Motion. All data comes from the `api` in
`src/features/characters/api`: cast generation calls the backend, everything else is still mocked.

## Requirements

- Node.js 20 or newer (`node -v`)

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

Cast generation needs the backend (see `../README.md`) on `http://127.0.0.1:8000` and Ollama.
The dev server and `npm run preview` forward `/api` to the backend, so no CORS setup is needed.

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

Nothing is saved yet: after a reload the cast is gone and has to be generated again.
When hosting the build, serve `index.html` for every path (SPA fallback); `npm run dev` and
`npm run preview` already do.

## Mock api switches

Add to the URL to test states without a model:

| Parameter | Effect |
|---|---|
| `?fail=card` | card update after editing fails, old card is kept |
| `?fail=chat` | "Ask AI to revise" fails |

Both can be combined: `?fail=card,chat`. To see a failed cast generation, stop Ollama or the backend.

## Structure

```
src/
  app/                    App (routes + page transitions + error banner), Providers
  shared/                 used by every feature
    api/errors.ts         ApiError, ApiErrorInfo, toErrorInfo
    api/http.ts           postJson: backend requests, failures → ApiError
    errors/               ErrorsProvider, useErrors (the banner's error)
    ui/                   Pill, Chip, Orb, Toast, ErrorBanner, icons
    ui/shadcn/            generated shadcn/ui components
    lib/  hooks/          cn(), useAutoGrow
  features/
    characters/           Character Creator
      api/                the only data source (backend + mocks)
      model/              types, labels, pure helpers (+ tests)
      store/              reducer, context, CastProvider
      pages/              prompt, generating, grid, detail
      paths.ts routes.tsx URLs and the route table
```

A new feature (e.g. plot) gets its own `features/<name>/` with the same folders, adds its
routes in `app/App.tsx` and its provider in `app/Providers.tsx`.

Fonts are bundled via `@fontsource`, so the app works offline.
