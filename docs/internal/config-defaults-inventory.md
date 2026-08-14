# Config-Defaults-Inventar — Dograh (dsactivi-2/dograh)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-28 |
| **Commit** | `02016bb65466ab73916bfc3a71f7727c7da66143` (`02016bb`) |
| **Branch** | `feature/stepsales-sales-api-mvp` |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Hinweis** | Defaults aus **Code / `.env.example` / Compose** — **nicht** aus einer Live-DB. Unklare Defaults sind als „kein expliziter Default“ markiert. |

**Zweck:** Operatoren und Entwickler sollen jede relevante Einstellung mit Default, Typ und Wirkung (true/false) auf Deutsch nachschlagen können.

---

## Übersichtstabelle (Auswahl der wichtigsten Flags)

| Einstellung | Datei / Ort | Default | Typ | Was ist das? | Wozu? | Wer ändert? |
|---|---|---|---|---|---|---|
| `is_superuser` | `api/db/models.py` → UserModel | `false` | bool | Plattform-Admin-Flag | Superuser-APIs (Impersonation, Cross-Org) | Superuser/Deploy/DB |
| `ENABLE_SIGNUP` | `api/.env.example`, `api/constants.py` | `true` | bool | Öffentliche Registrierung | `false` = nur Invite / Login | Ops |
| `ENABLE_AWS_S3` | `api/.env.example`, `api/constants.py` | `false` | bool | AWS/S3-Backend statt MinIO | Cloud-Recordings | Ops |
| `ENABLE_TELEMETRY` | `api/constants.py`, compose | `true` | bool | PostHog/Sentry-Telemetry | Analytics & Fehler | Ops |
| `ENABLE_ARI_STASIS` | `api/constants.py` | `false` | bool | Asterisk ARI/Stasis-Pfad | On-Prem Telephony | Ops |
| `FORCE_TURN_RELAY` | `api/constants.py` | `false` | bool | Nur TURN-Relay für WebRTC | Diagnose NAT/TURN | Dev/Ops |
| `SERIALIZE_LOG_OUTPUT` | `api/constants.py` | `false` | bool | JSON-Logs statt Klartext | Log-Pipelines | Ops |
| `MINIO_SECURE` | `api/constants.py` | `false` | bool | MinIO über HTTPS | TLS zum Object Store | Ops |
| `AUTH_PROVIDER` | `api/constants.py` | `"local"` | string | `local` oder `stack` | Auth-Backend | Ops |
| `DEPLOYMENT_MODE` | `api/constants.py` | `"oss"` | string | Deployment-Modus | Feature-Gates / Sentry | Ops |
| `external_pbx_integrations_enabled` | Org-Preferences | `false` | bool | Externe PBX-Integrationen | Feld-Mappings für Fremd-PBX | Org-Admin |
| `context_compaction_enabled` | Workflow-Config | `false` | bool | Kontext-Komprimierung im Call | Längere Calls, weniger Tokens | Agent-Builder |
| `ambient_noise.enabled` | Workflow-Config | `false` | bool | Ambient-Noise im Call | Realistischer Klang | Agent-Builder |
| `quota_enabled` | OrganizationModel | `false` | bool | Legacy-Quota (deprecated) | historisch; MPS übernimmt | Deploy (nicht nutzen) |
| `is_active` (API-Key) | APIKeyModel | `true` | bool | API-Key aktiv | Auth per X-API-Key | Org-Admin |
| `is_realtime` | AI Model Config | `false` | bool | Realtime-Pipeline statt STT→LLM→TTS | Latenz/Modellwahl | Org-Admin |

---

## A) Environment / Deploy

Quellen: [`api/.env.example`](../../api/.env.example), [`api/.env.test.example`](../../api/.env.test.example), [`api/constants.py`](../../api/constants.py), [`docker-compose.yaml`](../../docker-compose.yaml), [`docker-compose-local.yaml`](../../docker-compose-local.yaml), [`ui/.env.example`](../../ui/.env.example).

### A.1 Kern-Runtime

#### `ENVIRONMENT`
- **Ort:** `api/constants.py` → `os.getenv("ENVIRONMENT", Environment.LOCAL.value)` · `.env.example`
- **Default:** `"local"` (Enum: `local` | `production` | `test`)
- **Was ist das?** Laufzeit-Umgebung der API.
- **Werte:** `local` = Dev; `test` = Pytest (Logging wird u.a. abgeschaltet); `production` = Prod-Verhalten.
- **Wer ändert?** Ops / Compose.

#### `LOG_LEVEL`
- **Ort:** `api/constants.py` · `.env.example` (`DEBUG`) · Compose API oft `INFO`
- **Default (Code):** `"DEBUG"` · **Compose-API:** `"INFO"`
- **Was ist das?** Log-Schwelle (DEBUG/INFO/WARNING/ERROR).
- **Wozu:** Mehr Detail in Dev, weniger Rauschen in Prod.
- **Wer ändert?** Ops.

#### `LOG_FILE_PATH`
- **Ort:** `api/constants.py`
- **Default:** `None` (nur Konsole)
- **Was ist das?** Optionaler Dateipfad für Loguru-File-Handler.
- **Wer ändert?** Ops.

#### `LOG_ROTATION_SIZE` / `LOG_RETENTION` / `LOG_COMPRESSION`
- **Ort:** `api/constants.py`
- **Defaults:** `"100 MB"` · `"7 days"` · `"gz"`
- **Was ist das?** Rotation, Aufbewahrung und Kompression von Log-Dateien (wenn `LOG_FILE_PATH` gesetzt).
- **Wer ändert?** Ops.

#### `SERIALIZE_LOG_OUTPUT`
- **Ort:** `api/constants.py`
- **Default:** `false`
- **true:** Strukturierte/JSON-orientierte Log-Ausgabe (für Aggregatoren).
- **false:** Menschenlesbares Log-Format.
- **Wer ändert?** Ops.

#### `DATABASE_URL`
- **Ort:** `api/constants.py` → **Pflicht** (`os.environ["DATABASE_URL"]`)
- **Default in `.env.example`:** `postgresql+asyncpg://postgres:postgres@localhost:5432/postgres`
- **Test:** `…/test_db` in `.env.test.example`
- **Was ist das?** Async-SQLAlchemy-URL (Postgres + pgvector).
- **Wer ändert?** Ops — **niemals Secrets committen**.

#### `REDIS_URL`
- **Ort:** `api/constants.py` → **Pflicht**
- **Default in `.env.example`:** `redis://:redissecret@localhost:6379`
- **Was ist das?** Redis für ARQ-Jobs, Pub/Sub, Concurrency, Cache.
- **Wer ändert?** Ops.

#### `PUBLIC_BASE_URL` / `PUBLIC_HOST`
- **Ort:** `api/constants.py`
- **Default:** `None`
- **Was ist das?** Kanonische öffentliche Origin / Host. Daraus leiten sich Backend-URL, MinIO-Public und TURN-Host ab.
- **Wozu:** Remote-Deploy ohne viele Einzel-URLs.
- **Wer ändert?** Ops.

#### `BACKEND_API_ENDPOINT`
- **Ort:** `api/constants.py`
- **Default:** `PUBLIC_BASE_URL` oder `"http://localhost:8000"`
- **Was ist das?** Öffentliche API-URL für Webhooks, Callbacks, Embeds.
- **Hinweis:** Bei localhost/private IP versucht die API eine Cloudflare-Tunnel-URL zu resolven.
- **Wer ändert?** Ops.

#### `UI_APP_URL`
- **Ort:** `api/constants.py`
- **Default (Code):** `"http://localhost:3010"` · **`.env.example`:** `"http://localhost:3000"`
- **Was ist das?** Frontend-URL (Redirects, Links).
- **Hinweis:** Code-Default und `.env.example` weichen ab (3010 vs 3000). Compose-UI published **3010**.
- **Wer ändert?** Ops.

#### `CORS_ALLOWED_ORIGINS`
- **Ort:** `api/constants.py`
- **Default:** `""` → leere Liste (nur explizit gesetzte Origins)
- **Was ist das?** Komma-getrennte erlaubte Browser-Origins.
- **Wer ändert?** Ops.

#### `DEPLOYMENT_MODE`
- **Ort:** `api/constants.py`
- **Default:** `"oss"`
- **Was ist das?** Deployment-Kennzeichnung (u.a. Sentry-Gate: in OSS nur mit Telemetry).
- **Wer ändert?** Ops / SaaS-Deploy.

#### `FASTAPI_WORKERS`
- **Ort:** `docker-compose.yaml` (API-Env)
- **Default (Compose):** `1`
- **Was ist das?** Anzahl Uvicorn-Worker-Prozesse (Ports ab 8000, nginx least_conn).
- **Wer ändert?** Ops.

#### `FORWARDED_ALLOW_IPS`
- **Ort:** `docker-compose.yaml`
- **Default (Compose):** `"*"`
- **Was ist das?** Uvicorn vertraut `X-Forwarded-*` (wichtig hinter nginx für HTTPS-Webhook-Signaturen).
- **true-Äquivalent `*`:** Alle Peers vertrauen — Port 8000 härten!
- **Wer ändert?** Ops / Security.

#### `DOGRAH_DEVOPS_SECRET`
- **Ort:** `api/constants.py` · `.env.example`
- **Default:** `None` / Platzhalter `"change-me-dograh-devops-secret"`
- **Was ist das?** Shared Secret für Header `X-Dograh-Devops-Secret` (Active-Calls, Autoscale-Metric, Rolling-Update).
- **Ohne Secret:** geschützte Ops-Endpoints → 503.
- **Wer ändert?** Ops — starkes Secret in Prod.

#### `OSS_JWT_SECRET` / `OSS_JWT_EXPIRY_HOURS`
- **Ort:** `api/constants.py` · Compose **required**
- **Defaults:** `"change-me-in-production"` · `720` (30 Tage)
- **Was ist das?** JWT für lokale Email/Password-Auth (OSS).
- **Wer ändert?** Ops — **muss** in Prod gesetzt werden.

#### `AUTH_PROVIDER`
- **Ort:** `api/constants.py`
- **Default:** `"local"`
- **Werte:** `local` = Email/Password; `stack` = Stack Auth (SaaS).
- **Wer ändert?** Ops. UI liest `auth_provider` aus `/api/v1/health`.

#### `STACK_AUTH_PROJECT_ID` / `STACK_PUBLISHABLE_CLIENT_KEY`
- **Ort:** `api/constants.py`
- **Default:** `None`
- **Was ist das?** Öffentliche Stack-Auth-Client-Config (über Health an UI).
- **Wer ändert?** SaaS-Ops.

#### `DOGRAH_MPS_SECRET_KEY` / `MPS_API_URL`
- **Ort:** `api/constants.py`
- **Defaults:** `None` · `"https://services.dograh.com"`
- **Was ist das?** Managed Platform Services (Billing/Quota).
- **Wer ändert?** SaaS/Ops.

#### `TUNER_BASE_URL`
- **Ort:** `api/constants.py`
- **Default:** `"https://api.usetuner.ai"`
- **Was ist das?** Basis-URL der Tuner-Integration.
- **Wer ändert?** Ops.

### A.2 Signup & Telemetry

#### `ENABLE_SIGNUP`
- **Ort:** `api/constants.py` · `.env.example` · Compose `${ENABLE_SIGNUP:-true}`
- **Default:** `true`
- **true:** Öffentliche Registrierung erlaubt (Login zeigt Signup-Link).
- **false:** Invite-only — Signup-API/UI gesperrt.
- **UI-Fallback:** Wenn Health `signup_enabled` weglässt → UI nimmt `true` an (`ui/src/lib/auth/config.ts`).
- **Wer ändert?** Ops.

#### `ENABLE_TELEMETRY`
- **Ort:** `api/constants.py` · Compose API+UI
- **Default:** `true`
- **true:** PostHog/Sentry-Pfade aktiv (UI-Routes `api/config/posthog`, `api/config/sentry` lesen das Flag).
- **false:** Keine Produkt-Telemetry; in OSS auch Sentry-Init eingeschränkt.
- **Wer ändert?** Ops / Datenschutz.

#### `SENTRY_DSN` / `POSTHOG_API_KEY` / `POSTHOG_HOST`
- **Ort:** `api/constants.py`
- **Defaults:** `None` · `None` · `"https://us.i.posthog.com"`
- **Compose** setzt PostHog-Key hard-coded in Image-Env (upstream).
- **Wer ändert?** Ops.

### A.3 Storage (MinIO / S3)

#### `ENABLE_AWS_S3`
- **Ort:** `api/constants.py` · `api/enums.py` → `StorageBackend.get_current_backend()`
- **Default:** `false`
- **true:** Backend `s3` (AWS oder S3-kompatibel).
- **false:** Backend `minio` (lokal/OSS-Default).
- **Wer ändert?** Ops.

#### MinIO-Defaults (`api/constants.py` / `.env.example`)
| Key | Default |
|-----|---------|
| `MINIO_ENDPOINT` | `localhost:9000` (Compose: `minio:9000`) |
| `MINIO_PUBLIC_ENDPOINT` | `PUBLIC_BASE_URL` oder `http://localhost:9000` |
| `MINIO_ACCESS_KEY` | `minioadmin` |
| `MINIO_SECRET_KEY` | `minioadmin` |
| `MINIO_BUCKET` | `voice-audio` |
| `MINIO_SECURE` | `false` |

#### `MINIO_SECURE`
- **Default:** `false`
- **true:** HTTPS zum MinIO-Client.
- **false:** HTTP (typisch lokal).
- **Wer ändert?** Ops.

#### S3-Defaults
| Key | Default |
|-----|---------|
| `S3_BUCKET` | kein Default (env optional) |
| `S3_REGION` | `us-east-1` |
| `S3_ENDPOINT_URL` | `None` (AWS-Default) |
| `S3_SIGNATURE_VERSION` | `None` (botocore) |
| `S3_ADDRESSING_STYLE` | `None` (`auto`) |

### A.4 TURN / WebRTC

| Key | Default | Bedeutung |
|-----|---------|-----------|
| `TURN_HOST` | `PUBLIC_HOST` oder `"localhost"` | ICE/TURN-Host für Browser |
| `TURN_SECRET` | `None` (example: `dograh-turn-secret-…`) | Shared Secret für time-limited Creds |
| `TURN_PORT` | `3478` | UDP/TCP TURN |
| `TURN_TLS_PORT` | `5349` | TLS TURN |
| `TURN_CREDENTIAL_TTL` | `86400` (24h) | Credential-Gültigkeit (Sekunden) |

#### `FORCE_TURN_RELAY`
- **Default:** `false`
- **true:** Nur Relay-ICE-Kandidaten → erzwingt TURN (Diagnose).
- **false:** Normales ICE (Host/srflx/relay).
- **Wer ändert?** Dev/Ops bei NAT-Problemen.

### A.5 Telephony / Logging-Konstanten (Code)

#### `ENABLE_ARI_STASIS`
- **Default:** `false`
- **true:** Asterisk ARI/Stasis-Integrationspfad aktiv.
- **false:** Standard-Cloud-Provider (Twilio, Telnyx, …).
- **Wer ändert?** On-Prem-Ops.

#### `FILLER_SOUND_PROBABILITY`
- **Ort:** `api/constants.py` (Hardcode, kein Env)
- **Default:** `0.0`
- **Was ist das?** Wahrscheinlichkeit für Filler-Sounds im Call.
- **0.0:** Aus.

#### `VOICEMAIL_RECORDING_DURATION`
- **Default:** `5.0` Sekunden
- **Was ist das?** Dauer der Voicemail-Erkennung/Aufnahme-Logik.

### A.6 UI Environment

Quelle: [`ui/.env.example`](../../ui/.env.example)

| Key | Default / Example | Was |
|-----|-------------------|-----|
| `BACKEND_URL` | `http://localhost:8000` | Server-side URL zur API (SSR) |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Browser → API |
| `NEXT_PUBLIC_APP_URL` | unset (Origin) | Superadmin-Impersonation-Redirects |
| `NEXT_PUBLIC_NODE_ENV` | `development` | UI-Env-Kennung |
| `NEXT_PUBLIC_ONBOARDING_API_URL` | optional | Form-Submissions-Backend |
| `ENABLE_TELEMETRY` | Compose `true` | steuert PostHog/Sentry-Config-Routes |
| `NODE_ENV` (Compose UI) | `oss` | Compose-UI-Modus |
| `HOSTNAME` (Compose UI) | `0.0.0.0` | Next bindet alle Interfaces |

### A.7 Webhook-Delivery & Circuit Breaker (Code-Defaults)

#### `DEFAULT_WEBHOOK_DELIVERY_CONFIG` (`api/constants.py`)
| Key | Default | Env-Override |
|-----|---------|--------------|
| `max_attempts` | `5` | `WEBHOOK_DELIVERY_MAX_ATTEMPTS` |
| `base_delay_seconds` | `30` | `WEBHOOK_DELIVERY_BASE_DELAY_SECONDS` |
| `max_delay_seconds` | `600` | `WEBHOOK_DELIVERY_MAX_DELAY_SECONDS` |
| `timeout_seconds` | `30` | `WEBHOOK_DELIVERY_TIMEOUT_SECONDS` |

**Wozu:** Zuverlässige Outbound-Webhooks mit Exponential Backoff; nach max_attempts → `dead_letter`.

#### `DEFAULT_CIRCUIT_BREAKER_CONFIG`
| Key | Default | Bedeutung |
|-----|---------|-----------|
| `enabled` | `true` | Breaker an |
| `failure_threshold` | `0.5` | 50 % Fehler → Trip |
| `window_seconds` | `120` | 2-Minuten-Fenster |
| `min_calls_in_window` | `5` | Minimum Calls vor Trip |

#### `DEFAULT_CAMPAIGN_RETRY_CONFIG`
| Key | Default | Bedeutung |
|-----|---------|-----------|
| `enabled` | `true` | Retries an |
| `max_retries` | `1` | Max. Nachversuche |
| `retry_delay_seconds` | `120` | Pause zwischen Retries |
| `retry_on_busy` | `true` | Retry bei besetzt |
| `retry_on_no_answer` | `true` | Retry bei keine Antwort |
| `retry_on_voicemail` | `false` | **kein** Auto-Retry auf Voicemail |

Hinweis: Alembic-Server-Default an Campaigns kann historisch leicht abweichen (`max_retries: 2` in älterer Migration) — **Code-Konstante** ist die kanonische Default-Quelle für neue Logik.

#### `DEFAULT_ORG_CONCURRENCY_LIMIT`
- **Default:** `10` (Floor ≥ 1)
- **Env:** `DEFAULT_ORG_CONCURRENCY_LIMIT`
- **Was ist das?** Max. gleichzeitige Calls pro Org, wenn kein Org-Config-Override.
- **Wer ändert?** Ops / Org-Admin (Org-Config-Key `CONCURRENT_CALL_LIMIT`).

---

## B) User & Admin (inkl. Superuser)

Quellen: [`api/db/models.py`](../../api/db/models.py), [`api/services/auth/depends.py`](../../api/services/auth/depends.py), [`api/routes/superuser.py`](../../api/routes/superuser.py), [`api/schemas/onboarding_state.py`](../../api/schemas/onboarding_state.py), UI `superadmin/`, `lib/utils.ts`.

#### `is_superuser`
- **Ort:** `UserModel.is_superuser`
- **Default:** `false`
- **Was ist das?** Plattform-Administrator-Flag in der lokalen User-Tabelle.
- **true:** Darf Superuser-Routen nutzen (`get_superuser` → sonst 403). Funktionen u.a.:
  - Impersonation (`POST /api/v1/superuser/impersonate`) — nur sinnvoll mit Stack Auth
  - Cross-Org Workflow-Run-Listen / Support-Sicht
  - UI: Superadmin-Bereich (`ui/src/app/superadmin`, `is_superuser` in `lib/utils.ts`)
- **false:** Normaler Org-User — nur eigene Organisation, keine Superuser-APIs.
- **Wozu:** Self-Host-Betreiber, Support, Notfall-Admin.
- **Wer ändert?** Deploy/DB (manuell setzen); **kein** Self-Service-Toggle für normale User.

#### Weitere User-Defaults
| Feld | Default | Bedeutung |
|------|---------|-----------|
| `selected_organization_id` | `None` | Aktuell gewählte Org |
| `email` | `None` | Optional; unique case-insensitive wenn gesetzt |
| `password_hash` | `None` | Nur local-auth |
| `is_superuser` | `false` | s.o. |

#### Onboarding (`UserConfigurationKey.ONBOARDING`)
| Feld | Default | Bedeutung |
|------|---------|-----------|
| `completed_at` | `None` | Zeitpunkt Abschluss |
| `skipped` | `false` | User hat Onboarding übersprungen |
| `seen_tooltips` | `[]` | Gesehene UI-Tooltips |
| `completed_actions` | `[]` | Erledigte Milestone-Actions |

- **skipped=true:** Gate gilt als erledigt ohne Formular.
- **skipped=false + completed_at=None:** Post-Signup-Gate kann greifen.

#### API-Keys
| Feld | Default | Bedeutung |
|------|---------|-----------|
| `is_active` | `true` | Key akzeptiert Auth |
| `is_active=false` | — | Key deaktiviert, Requests 401 |

#### Superuser-Zugang
- Dependency: `get_superuser` prüft Auth + `user.is_superuser`.
- **Nicht** verwechseln mit Org-Admin / Stack-Team-Rollen: das ist ein **Dograh-DB-Flag**.

---

## C) Organisation

Quellen: `OrganizationModel`, `OrganizationPreferences`, `OrganizationConfigurationKey`, Usage/Quota-Felder.

### C.1 OrganizationModel (Legacy-Quota — deprecated)
| Feld | Default | Hinweis |
|------|---------|---------|
| `quota_type` | `"monthly"` | Deprecated — MPS besitzt Ledger |
| `quota_dograh_tokens` | `0` | Deprecated |
| `quota_reset_day` | `1` | Deprecated |
| `quota_start_date` | nullable | Deprecated |
| `quota_enabled` | `false` | Deprecated |

#### `quota_enabled`
- **Default:** `false`
- **true (historisch):** Org-Quota-Enforcement lokal.
- **false:** Kein lokales Quota-Gate (Standard; MPS-Pfad).
- **Wer ändert?** Nicht manuell für neue Deploys empfohlen.

### C.2 OrganizationPreferences
| Feld | Default | Bedeutung |
|------|---------|-----------|
| `test_phone_number` | `None` | Nummer für Testanrufe |
| `timezone` | `None` (UI-Fallback: Browser-TZ oder `UTC`) | Anzeige/Scheduling |
| `external_pbx_integrations_enabled` | `false` | Externe PBX-Features |

#### `external_pbx_integrations_enabled`
- **true:** UI/API erlauben externe-PBX-Feldmappings & Integrationen.
- **false:** Feature aus (Default, sicherer).
- **Wer ändert?** Org-Admin in Settings.

### C.3 Org-Configuration-Keys (kein fester bool-Default im Schema)
Gespeichert als JSON pro Key (`organization_configurations`):

| Key | Zweck |
|-----|-------|
| `CONCURRENT_CALL_LIMIT` | Override Concurrent Calls (`{"value": N}`) |
| `TELEPHONY_CONFIGURATION` | Provider-Configs + active |
| `TWILIO_CONFIGURATION` | Deprecated Legacy |
| `LANGFUSE_CREDENTIALS` | Org-Tracing |
| `MODEL_CONFIGURATION_V2` | AI v2 Config |
| `ORGANIZATION_PREFERENCES` | Preferences JSON |
| `MODEL_CONFIGURATION_PREFERENCES` | Deprecated Fallback |

### C.4 Concurrency
- Default-Limit: **10** parallele Calls/Org (`DEFAULT_ORG_CONCURRENCY_LIMIT`).
- Override: Org-Config `CONCURRENT_CALL_LIMIT`.
- Bei Limit: Telephony-Error `CONCURRENT_CALL_LIMIT`, PostHog-Event `usage_concurrent_call_limit_reached`.

---

## D) Workflow Configuration

Quelle: [`api/schemas/workflow_configurations.py`](../../api/schemas/workflow_configurations.py)

### Konstanten
| Name | Default | Bedeutung |
|------|---------|-----------|
| `DEFAULT_MAX_CALL_DURATION_SECONDS` | `300` (5 Min) | Soft-Default Call-Länge |
| `MAX_CALL_DURATION_SECONDS` | `1200` (20 Min) | Hard-Ceiling (≤ stale_call_timeout) |
| `DEFAULT_MAX_USER_IDLE_TIMEOUT_SECONDS` | `10.0` | Idle bis User-Timeout |
| `DEFAULT_SMART_TURN_STOP_SECS` | `2.0` | Smart-Turn Stop |
| `DEFAULT_TURN_START_STRATEGY` | `"default"` | Turn-Start-Strategie |
| `DEFAULT_TURN_START_MIN_WORDS` | `3` | Min. Wörter bei `min_words` |
| `DEFAULT_PROVISIONAL_VAD_PAUSE_SECS` | `1.5` | VAD-Pause |
| `DEFAULT_TURN_STOP_STRATEGY` | `"transcription"` | Turn-Stop |
| `DEFAULT_CONTEXT_COMPACTION_ENABLED` | `false` | Kontext-Kompaktion |

### Ambient Noise
| Feld | Default | true/false |
|------|---------|------------|
| `ambient_noise_configuration.enabled` | `false` | an/aus Hintergrundgeräusch |
| `ambient_noise_configuration.volume` | `0.3` | Lautstärke 0–1 |

### WorkflowConfigurationDefaults (Felder)
| Feld | Default | Typ / Werte |
|------|---------|-------------|
| `max_call_duration` | `300` | int, 1…1200 Sek. |
| `max_user_idle_timeout` | `10.0` | float Sek. |
| `smart_turn_stop_secs` | `2.0` | float |
| `turn_start_strategy` | `"default"` | `default` \| `min_words` \| `provisional_vad` |
| `turn_start_min_words` | `3` | int |
| `provisional_vad_pause_secs` | `1.5` | float |
| `turn_stop_strategy` | `"transcription"` | `transcription` \| `turn_analyzer` |
| `dictionary` | `""` | Custom-Wörterbuch |
| `context_compaction_enabled` | `false` | bool |
| `external_pbx_field_mappings` | `[]` | max 100 Mappings |

#### `context_compaction_enabled`
- **true:** Längerer Dialog-Kontext wird verdichtet (Token-Sparsamkeit).
- **false:** Keine Kompaktion (Default).

#### `max_call_duration`
- **Wozu:** Harte Call-Obergrenze pro Workflow; schützt Concurrency-Slots und Kosten.
- **Wer ändert?** Agent-Builder / Workflow-Settings-UI.

### Workflow / Run Model-Defaults (DB)
| Feld | Default | Ort |
|------|---------|-----|
| Workflow `status` | `active` | WorkflowModel |
| Workflow-Definition `version`/`status` | `"published"` | Definition |
| Run `call_type` | `outbound` | WorkflowRunModel |
| Run `state` | `initialized` | WorkflowRunModel |
| Run `is_completed` | `false` | WorkflowRunModel |
| Run `storage_backend` | `"s3"` (Enum server_default) | **Hinweis:** Runtime wählt via `ENABLE_AWS_S3` (MinIO wenn false) — Spalten-Default ist historisch `s3` |

### Call Disposition
- `call_disposition_codes` Default: `{}` (leer) — Org/Workflow pflegt Codes.

---

## E) AI Provider Defaults

Quellen: [`api/services/configuration/defaults.py`](../../api/services/configuration/defaults.py), [`api/services/configuration/registry.py`](../../api/services/configuration/registry.py), [`api/schemas/ai_model_configuration.py`](../../api/schemas/ai_model_configuration.py).

### E.1 Default-Provider-Mapping (neue User/Configs)
| Service | Default-Provider | Config-Klasse |
|---------|------------------|---------------|
| `llm` | **openai** | `OpenAILLMService` |
| `tts` | **elevenlabs** | `ElevenlabsTTSConfiguration` |
| `stt` | **deepgram** | `DeepgramSTTConfiguration` |
| `embeddings` | **openai** | `OpenAIEmbeddingsConfiguration` |

API-Keys kommen aus Env `{PROVIDER}_API_KEY` (z.B. `OPENAI_API_KEY`). Fehlt der Key → Provider-Config bleibt `None`.

### E.2 Wichtige Modell-Defaults (Registry Field defaults)

| Provider / Service | Feld | Default |
|--------------------|------|---------|
| OpenAI LLM | `model` | `gpt-4.1` |
| OpenAI LLM | `base_url` | `https://api.openai.com/v1` |
| Google LLM | `model` | `gemini-2.5-flash` |
| Groq LLM | `model` | `llama-3.3-70b-versatile` |
| OpenRouter LLM | `model` | `openai/gpt-4.1` |
| Azure LLM | `model` | `gpt-4.1-mini` |
| Dograh LLM | `model` | `default` |
| AWS Bedrock LLM | `model` | `us.amazon.nova-pro-v1:0` |
| Deepgram STT | `model` | `nova-3-general` |
| Deepgram STT | `language` | `multi` |
| OpenAI STT | `model` | `gpt-4o-transcribe` |
| Dograh STT | `model` / `language` | `default` / `multi` |
| ElevenLabs TTS | `voice` | `21m00Tcm4TlvDq8ikWAM` |
| ElevenLabs TTS | `model` | `eleven_flash_v2_5` |
| ElevenLabs TTS | `speed` | `1.0` |
| ElevenLabs TTS | `base_url` | `https://api.elevenlabs.io` |
| Deepgram TTS | `voice` | `aura-2-helena-en` |
| OpenAI TTS | `model` / `voice` | `gpt-4o-mini-tts` / `alloy` |
| Dograh TTS | `model` / `voice` / `speed` | `default` / `default` / `1.0` |
| OpenAI Embeddings | `model` | `text-embedding-3-small` |
| Dograh Embeddings | `model` | `dograh_embedding_v1` |
| OpenAI Realtime | `model` / `voice` | `gpt-realtime-2` / `alloy` |
| Grok Realtime | `model` / `voice` | `grok-voice-think-fast-1.0` / `ara` |

### E.3 Org AI Config v2
| Feld | Default / Regel |
|------|-----------------|
| `version` | `2` |
| `mode` | `"dograh"` **oder** `"byok"` (kein stiller Default — muss gesetzt sein) |
| Dograh managed `voice` | `"default"` |
| Dograh managed `speed` | `1.0` (0.5…2.0) |
| Dograh managed `language` | `"multi"` |
| `is_realtime` (effective) | `false` |
| BYOK `mode` | `"pipeline"` oder `"realtime"` |

**EffectiveAIModelConfiguration.is_realtime**
- **true:** Realtime-Provider-Pfad.
- **false:** Klassische Pipeline STT→LLM→TTS (Default-Annahme).

---

## F) Telephony / Campaign / Quota

### F.1 Telephony Models
| Feld | Default | Bedeutung |
|------|---------|-----------|
| TelephonyConfig `is_default_outbound` | `false` | Standard-Outbound-Provider |
| PhoneNumber `enabled` | `true` | Nummer nutzbar |
| PhoneNumber `is_default_caller_id` | `false` | Default-Caller-ID |
| Integration `is_active` | `true` | Integration an |
| Integration `action` | `"All Calls"` | Wann feuern |

### F.2 Campaign
| Feld | Default | Bedeutung |
|------|---------|-----------|
| source type | oft `"csv"` | Lead-Quelle |
| state / counters | `0` / `"pending"` | Fortschritt |
| `retry_config` | `DEFAULT_CAMPAIGN_RETRY_CONFIG` | s. Abschnitt A.7 |
| circuit breaker | `DEFAULT_CIRCUIT_BREAKER_CONFIG` | Auto-Pause bei Fehlerrate |

### F.3 Tool / Trigger / Webhook
| Feld | Default |
|------|---------|
| Tool `status` | `active` |
| Trigger `state` | `active` |
| Webhook delivery `status` | `pending` |
| Webhook `attempt_count` | `0` |
| Webhook `max_attempts` | `5` |

### F.4 Knowledge Base / Recordings
| Feld | Default / Status |
|------|------------------|
| Document processing | `pending` |
| Chunk retrieval modes | schema-abhängig |
| Recording storage_backend server_default | `s3` (siehe Workflow-Hinweis) |

---

## G) UI Feature Flags

Quellen: `ui/src/lib/auth/config.ts`, `ui/src/app/api/config/*`, Health-Endpoint, Superadmin-Nav.

| Flag / Signal | Quelle | Default | Wirkung |
|---------------|--------|---------|---------|
| `signupEnabled` | Health `signup_enabled` ← `ENABLE_SIGNUP` | `true` | Signup-Link / Page |
| `authProvider` | Health `auth_provider` | `"local"` | local vs Stack UI |
| `turn_enabled` | Health: `bool(TURN_SECRET)` | false wenn Secret fehlt | TURN-Credentials-API |
| `force_turn_relay` | Health ← `FORCE_TURN_RELAY` | `false` | Browser ICE nur relay |
| PostHog UI | `ENABLE_TELEMETRY === 'true'` | true in Compose | Analytics |
| Sentry UI | `ENABLE_TELEMETRY === 'true'` | true in Compose | Error-Tracking |
| Superadmin-Nav | `user.is_superuser` | `false` | Admin-UI sichtbar |
| Org external PBX switch | Preferences | `false` | Settings-Toggle |

**Seiten mit Settings-Bezug (Reuse, keine neuen Flags nötig):**
- `/settings` — Org/User Settings
- `/model-configurations` — AI v2
- `/telephony-configurations` — Telephony
- `/superadmin` — Superuser
- `/campaigns` — inkl. Advanced Settings (Retry)
- `/workflow/[id]/settings` — Workflow-Config

---

## H) Observability / Tracing

| Einstellung | Default | Bedeutung |
|-------------|---------|-----------|
| `LANGFUSE_HOST` / `PUBLIC_KEY` / `SECRET_KEY` | unset | Global-Tracing; alternativ Org-Credentials in UI `/settings` |
| Tracing aktiv | wenn Credentials vorhanden | Auto-On bei Keys |
| `ENABLE_TELEMETRY` | `true` | PostHog + Sentry-Gates |
| `SENTRY_DSN` | unset | Fehler-Tracking |
| Loop-lag Metrics | runtime | `/health/active-calls`, Autoscale |
| Active call count | Redis/fleet | KEDA / drain |

**Langfuse:** Kein Bool-Flag „enabled“ — **Präsenz der Credentials** steuert Aktivierung (global env **oder** org `LANGFUSE_CREDENTIALS`).

---

## Anhang 1 — Boolean-Schnellreferenz

| Flag | Default | true | false |
|------|---------|------|-------|
| `ENABLE_SIGNUP` | true | Registrierung offen | Invite-only |
| `ENABLE_AWS_S3` | false | S3-Backend | MinIO |
| `ENABLE_TELEMETRY` | true | Analytics an | Analytics aus |
| `ENABLE_ARI_STASIS` | false | ARI-Pfad | Standard-Cloud-Telephony |
| `FORCE_TURN_RELAY` | false | Nur TURN | Normales ICE |
| `SERIALIZE_LOG_OUTPUT` | false | JSON-Logs | Text-Logs |
| `MINIO_SECURE` | false | HTTPS MinIO | HTTP |
| `is_superuser` | false | Plattform-Admin | Normal-User |
| `quota_enabled` | false | Legacy-Quota an | aus (empfohlen) |
| `external_pbx_integrations_enabled` | false | PBX-Integrationen | aus |
| `context_compaction_enabled` | false | Kompaktion an | aus |
| `ambient_noise.enabled` | false | Noise an | aus |
| `is_realtime` | false | Realtime-AI | Pipeline |
| `is_active` (API key) | true | Key gilt | Key tot |
| `campaign retry.enabled` | true | Retries | keine Retries |
| `circuit_breaker.enabled` | true | Auto-Pause | nie trip |
| `retry_on_voicemail` | false | Retry Voicemail | kein Retry |
| Onboarding `skipped` | false | übersprungen | Gate möglich |

---

## Anhang 2 — Quellen-Checkliste (gescannt)

- [x] `api/.env.example`, `api/.env.test.example`
- [x] `ui/.env.example`
- [x] `docker-compose.yaml`, `docker-compose-local.yaml`
- [x] `api/constants.py`, `api/enums.py`
- [x] `api/db/models.py` (User, Org, Workflow, Campaign, Tools, Stepsales, …)
- [x] `api/schemas/organization_preferences.py`, `workflow_configurations.py`, `onboarding_state.py`, `ai_model_configuration.py`
- [x] `api/services/configuration/defaults.py`, `registry.py`, `options/*`
- [x] `api/routes/superuser.py`, `api/services/auth/depends.py`
- [x] UI auth config, settings, superadmin, OrganizationPreferencesSection
- [x] Campaign retry / circuit breaker constants
- [ ] Live-DB-Werte — **bewusst nicht** (Defaults aus Code)

---

## Anhang 3 — Offene / uneinheitliche Defaults

1. **`UI_APP_URL`:** Code-Default `http://localhost:3010` vs `.env.example` `http://localhost:3000` — Compose UI Port **3010**.
2. **`storage_backend` server_default `s3`** vs Runtime-Backend MinIO bei `ENABLE_AWS_S3=false` — Spalten-Default historisch.
3. **Campaign `retry_config` server_default in Migration** kann von `DEFAULT_CAMPAIGN_RETRY_CONFIG` leicht abweichen — bei Audits beide prüfen.
4. **AI v2 `mode`:** kein stiller Default — muss `dograh` oder `byok` gesetzt sein.

---

*Ende Inventar · Commit `02016bb` · Defaults nur aus Code-Belegen.*
