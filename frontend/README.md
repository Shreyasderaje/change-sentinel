# Change Sentinel frontend

An independent Next.js frontend for Vercel. The Streamlit application at the repository root remains the working detection workflow; this frontend is a visual workspace and does not claim to run detection.

## Local development

```bash
npm install
npm run dev
```

Production build check:

```bash
npm run build
npm run typecheck
```

## Deploy to Vercel

Import `Shreyasderaje/change-sentinel` as a new Vercel project and set **Root Directory** to `frontend`. Vercel detects Next.js and uses `npm install` / `npm run build` by default. No root-level Render files or settings need to change. The live detection link is configured in `components/dashboard.tsx`.
