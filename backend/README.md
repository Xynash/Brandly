# Brandly API

Start PostgreSQL with `docker compose up -d db` from the repository root. From `backend`, activate your virtual environment, install `requirements.txt`, and create `.env` from `.env.example` if needed. Run `python -m alembic upgrade head` and `python -m uvicorn app.main:app --reload`. Swagger is at http://127.0.0.1:8000/docs.

## Authentication

Sign up with `POST /auth/signup` using `email`, `password`, `full_name`, and `agency_name`. The account becomes its new agency's admin. Passwords must be 15 to 256 characters. Sign in again with `POST /auth/login` using email and password. Send the returned access token in the Authorization bearer header. Sessions expire after 24 hours and `POST /auth/logout` revokes the current session. Use HTTPS outside local development.

`GET /agencies/current` returns the signed-in user's agency. A database operator can create a writer under an existing agency and enter their password interactively.

```powershell
python -m app.provision_user --agency-id AGENCY_UUID --email writer@example.com --name "Example Writer"
```

Existing user records are preserved by the migration. Records without a password cannot sign in through the password endpoint. Email confirmation and password recovery are outside the current signup flow.

For a local demo, set `AUTH_MODE=development`, run `python -m app.seed`, and pass the printed agency UUID as `X-Agency-Id`. Use the default password mode in shared environments. `LLM_PROVIDER=mock` exercises the generation flow without provider credentials.

## Generation, presets, and websites

- `POST /clients/{client_id}/generate` returns checked copy or a review flag. A flagged draft stays in generation history for review.
- `POST /clients/{client_id}/generate/stream` takes the same JSON body. Consume it with a streaming POST client. Events are `started`, `completed`, `review_required`, and `error`. Provider output is buffered until the compliance scan finishes.
- `GET /presets` lists versioned editorial guardrails and their sources. Select them with `preset_ids` on `PUT /clients/{client_id}/hub`. Generation and the standalone scan route use the same terms.
- `POST /clients/{client_id}/hub/import` takes a public website URL and returns a proposed hub. Review it before saving through `PUT /clients/{client_id}/hub`. A configured model is needed to generate the JSON draft.

## Model providers and agency keys

Set `LLM_PROVIDER` to `gemini`, `openai`, or `anthropic` and configure its model and optional server API key in `.env`. Agency admins can PUT an `api_key` to `/agencies/current/provider-keys/{provider}` to override the configured server key for their own agency. DELETE removes the override. Generate a `PROVIDER_KEY_ENCRYPTION_KEY` and store it alongside your deployment secrets. Keep the same encryption key when redeploying so existing overrides can still be opened.

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Tests

Run `python -m pytest -q` from `backend`. Tests use `brandly_test` on port 5433 by default and accept `TEST_DATABASE_URL` for a separate PostgreSQL instance. Use a database name ending in `_test`.
