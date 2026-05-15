# JUNERDD Skills — web

Next.js (App Router) marketing site for the skills collection.

**Live (production):** [https://junerdd-skills.vercel.app](https://junerdd-skills.vercel.app)

## Local development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Content architecture

The site is structured as a CMS-ready content app. UI routes and components read
skills through `src/lib/content/provider.ts` instead of importing the static
catalog directly.

Current provider:

- `src/lib/content/static-provider.ts` reads the existing in-repo catalog from
  `src/lib/skills-data.ts`.
- `src/lib/content/types.ts` owns the public skill data shape used by pages and
  components.
- `src/lib/content/urls.ts` owns lightweight constants and URL/install helpers
  that are safe for client components.

When replacing the static catalog with a headless CMS, add a new provider beside
`static-provider.ts` and switch the exports in `provider.ts`. Keep the page and
component props stable so the UI remains provider-agnostic.

## Deploy on Vercel (recommended)

This app lives in the monorepo subdirectory **`web/`**. In Vercel, the project **Root Directory must be `web`**, not the repository root.

1. [Import the Git repository](https://vercel.com/new) into Vercel.
2. Set **Root Directory** → **`web`**, **Framework Preset** → Next.js (auto-detected).
3. **Production** environment variable: **`NEXT_PUBLIC_SITE_URL`** = your canonical production URL without a trailing slash (must match the Production primary domain, including `https://`). Copy from [`.env.example`](./.env.example).
4. Deploy. Previews will use the generated `VERCEL_URL` when `NEXT_PUBLIC_SITE_URL` is unset; Production should always set `NEXT_PUBLIC_SITE_URL` once the domain is finalized.

`vercel.json` in this folder sets framework metadata and conservative security headers.

## Link the GitHub repository to the live site

After production is live:

1. GitHub → repository **Settings** → **General** → **Website** → paste the same production URL used in `NEXT_PUBLIC_SITE_URL`.

The site already links out to the GitHub repository from the header and hero CTAs.

## Internationalization

The app uses `next-intl` with an unprefixed default English locale and a
prefixed Chinese locale:

- English: `/`, `/skills/<slug>`
- Chinese: `/zh-CN`, `/zh-CN/skills/<slug>`
- Routing config: `src/i18n/routing.ts`
- Request messages: `src/i18n/request.ts`
- Locale negotiation proxy: `src/proxy.ts`
- Shared UI dictionaries and skill catalog overrides: `src/lib/i18n/`

Keep user-facing pages under `src/app/[locale]/` so metadata, navigation, and
static generation stay locale-aware.
