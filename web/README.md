# web — Demo page (Module 10)

Plain HTML + CSS + JavaScript, served by FastAPI at `/` (no build step, no framework).

- `index.html` — the layout: inputs (clips, mic, text), strong AI vs Pehchaan, clarify, reminders, scoreboard, demo mode
- `style.css` — the look (navy / warm white / lime; Space Grotesk + Inter)
- `app.js` — talks to `/api/...` only; the OpenAI key never reaches the browser
- `favicon.svg` — the tab icon

Run `uvicorn app.main:app --reload` and open http://localhost:8000.
