# JEFF Agent Wrapper — v2

## What's Done
- FastAPI /chat endpoint with real token streaming via persistent Node sidecar
- Mode routing: investor, business_model, customer, campaign_builder, financial
- CORS configured for juststrtup.com
- Session memory (in-memory, keyed by session_id, 2hr TTL)
- Persistent Node sidecar (Express on :3001) — no per-request process spawn
- TypeScript compiled to JS at build time (no tsx in production)
- POST /export/xlsx — openpyxl Excel export
- POST /export/pdf — reportlab PDF export
- 24-hour token limits: 150,000 tokens/session, X-Tokens-Remaining header, 429 on cap
- Updated jeff-ui.html: real streaming, Campaign Builder tab, export buttons, quota indicator

## What's Pending / Known Limitations
- Token ledger and session store are in-memory — will reset on dyno restart. **Needs Redis for multi-instance production.**
- OpenAI platform system prompts for Campaign Builder are managed by the client — not in this repo.
- No auth/API key gate on /chat (handled by WordPress proxy layer)

## What I Tested
- [ ] POST /chat on live Render URL — real streaming tokens arrive in browser
- [ ] Session memory — multi-turn conversation maintains context across requests
- [ ] Mode validation — invalid mode returns 422
- [ ] /export/xlsx — downloads valid .xlsx file
- [ ] /export/pdf — downloads valid .pdf file  
- [ ] 429 response when token limit is hit (simulated by lowering limit)
- [ ] jeff-ui.html streaming visible in Chrome and Safari
- [ ] Sidecar health check on startup

## Environment Variables Required
See .env.example
