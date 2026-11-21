# Pehchaan — Learning Notes

One section per module: what we built, how it works, key concepts, and questions a judge might ask.

---

## Module 1 — Project setup

### What we built
The base of the project, with no "AI" yet:
- A **FastAPI** web app with one endpoint, `GET /health`, that returns `{"status": "ok", "project": "Pehchaan"}`.
- A **settings file** (`app/config.py`) that reads the OpenAI key and model names from a `.env` file.
- A **check script** (`scripts/check_openai.py`) that makes one tiny OpenAI call to prove the key works.
- A **test** (`tests/test_health.py`) that checks `/health` automatically.
- The folder structure for every later module, plus `README.md`, `CLAUDE.md`, `.gitignore`, `.env.example`.

### How it works
1. When the app starts, `app/config.py` creates one `Settings` object. pydantic-settings fills each field
   from environment variables or `.env`, and uses the default when a value is missing.
2. `app/main.py` creates the FastAPI `app` and registers `/health`.
3. **Uvicorn** is the server. It listens on a port (8000), receives HTTP requests and hands them to FastAPI.
4. FastAPI calls our `health()` function and turns the returned dict into JSON.
5. In tests, **TestClient** calls the app in memory, without a real server, and we check the reply with `assert`.

### Key concepts
- **Virtual environment (venv):** a private folder of Python packages just for this project. Each project gets
  its own versions, so projects don't conflict, and AWS can reproduce the exact setup.
- **requirements.txt + pinning:** the list of packages with exact versions (`fastapi==0.115.6`).
  Pinning means "install this exact version", so the code behaves the same on every machine.
- **FastAPI:** a Python web framework. You write normal functions, mark them with `@app.get("/path")`,
  and FastAPI turns them into HTTP endpoints. It also builds interactive docs at `/docs` for free.
- **Uvicorn:** an ASGI server, the program that actually runs the web app and talks to the network.
  (ASGI is the standard interface between Python web apps and servers.)
- **Endpoint:** a URL plus an HTTP method (GET, POST...) that the app answers. `GET /health` is one.
- **Health check:** a cheap endpoint that answers "I'm alive". Deploy tools and load balancers call it to
  decide whether the app is running.
- **Environment variables / `.env`:** settings that live outside the code. Secrets like API keys go here,
  never in source code. `.env` is git-ignored. `.env.example` shows the variable *names* only.
- **pydantic-settings:** reads env variables into a typed Python class. It checks types and fills defaults.
- **SecretStr:** a pydantic type that prints as `**********`, so a key can't leak into logs by accident.
- **pytest / TestClient:** pytest finds functions named `test_*` and runs them. A failing `assert` means a failed test.
  TestClient sends fake HTTP requests straight to the app.
- **.gitignore:** tells git which files never to track (secrets, venv, caches).
- **Exit code:** a number a program returns when it ends. 0 means success, anything else means failure.
  `check_openai.py` returns 1 on errors, so scripts and CI can detect the failure.

### A real bug we hit (and fixed)
The first version of `check_openai.py` printed emoji (✅ ❌). Some Windows terminals use an old text encoding
(cp1252) that has no emoji, so Python crashed with `UnicodeEncodeError`. We switched to plain `[OK]` /
`[ERROR]` markers, which work in every terminal. Lesson: test on the platform you'll actually demo on.

We also pinned `anyio==4.8.0`. A newer anyio caused a deprecation warning inside FastAPI's test client.

### Questions a judge might ask about this module
- **Why FastAPI and not Flask?** FastAPI has built-in data validation with Pydantic, automatic API docs at `/docs`,
  and async support. Those suit an API that calls OpenAI. It is also simple to explain.
- **How do you keep your API key safe?** It lives only in `.env`, which is in `.gitignore`. The code reads it
  through pydantic-settings as a `SecretStr`, so it is never hard-coded, committed or printed.
- **Why have a /health endpoint at all?** It is the simplest proof the server is up. On AWS it lets us
  (and any load balancer) check the app is alive without calling OpenAI.
- **Why pin versions?** So the demo machine and the EC2 server install exactly what we tested. No surprise upgrades.
- **Why put model names in config?** So we can swap models (e.g. a newer transcription model) with a one-line `.env`
  change and compare them, without touching code.
- **Why write tests in a 28-hour hackathon?** Each module builds on the last. A quick test catches a broken
  import or config immediately, which is cheaper than finding it during the demo.
