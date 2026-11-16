# Deployment

Status: not deployed yet.

- Live URL: _TBD_ (`POST <url>/score`, `GET <url>/health`)
- Repository: _TBD_

## Steps (Vercel)

1. Push this folder to a GitHub repository and import it in Vercel. If the repository contains the whole take-home, set Vercel's Root Directory to `test-1-build/submission`.
2. Set environment variables: `OPENAI_API_KEY` (required) and `OPENAI_MODEL` (optional, default `gpt-5.4-mini-2026-03-17`).
3. Deploy. `vercel.json` sets the function `maxDuration` to 30 seconds.
4. Check `GET /health` from a logged-out browser, then POST the brief's samples to `/score` and record latency here.
