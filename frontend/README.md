# Anton — Character Creator (frontend)

Web frontend for the Character Creator: premise → generated cast → character editing.
Vite + React + TypeScript + Tailwind + shadcn/ui + Motion. All data comes from a mock `api`
(`src/api`), no backend is needed yet.

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
  app/                    App: screens + error banner
  shared/                 used by every feature
    api/errors.ts         ApiError, ApiErrorInfo
    ui/                   Pill, Chip, Orb, Toast, ErrorBanner, icons
    ui/shadcn/            generated shadcn/ui components
    lib/  hooks/          cn(), useAutoGrow
  features/
    characters/           Character Creator
      api/                mock api — the only data source
      model/              types, labels, pure helpers (+ tests)
      store/              reducer, context, CastProvider
      pages/              prompt, generating, grid, detail
```

A new feature (e.g. plot) gets its own `features/<name>/` with the same folders.

Fonts are bundled via `@fontsource`, so the app works offline.
