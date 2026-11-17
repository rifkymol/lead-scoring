# Deployment

Status: deployed on Vercel (Hobby plan), verified 2026-11-17.

- Live URL: https://lead-scoring-eight.vercel.app (`POST /score`, `GET /health`)
- Repository: https://github.com/rifkymol/lead-scoring (public)

## Verified on 2026-11-17

- `GET /health` returns 200 from a logged-out client (no Vercel deployment protection).
- `POST /score` with an empty body returns 422 in the documented error format.
- The brief's four transcripts sent to the live URL 5 times each (20 calls): all 200, all exact
  (S001 85 Hot, S002 20 Cold, S003 50 Warm, L001 70 Warm). Latency min 1.47 s, median 1.99 s,
  max 2.96 s; the first call after deploy took about 4 s. Limit is 30 s.
- Before the fix below, one of 8 calls returned 502: the model marked S002's distribution network
  "absent" without evidence. An evidence-less "absent"/"no_history" is now recorded as unknown,
  which the extraction rules already define as the meaning of silence.

## Steps (Vercel CLI)

1. `npx vercel link --yes --project lead-scoring` from this folder.
2. `npx vercel env add OPENAI_API_KEY production` (type the key at the prompt). `OPENAI_MODEL` is
   optional, default `gpt-5.4-mini-2026-03-17`.
3. `npx vercel deploy --prod --yes`. `vercel.json` sets the function `maxDuration` to 30 seconds.
   Environment variable changes need a redeploy.
4. Check `GET /health` logged out, then POST the brief's samples to `/score`.

Git auto-deploy is not connected (the Vercel GitHub app isn't installed), so deploys run from the CLI.
