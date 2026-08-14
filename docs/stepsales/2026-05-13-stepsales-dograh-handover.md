# Handover – Dograh / Stepsales – 2026-05-13

## Scope completed
- Fixed the optional `sdk` container so Dograh SDK examples run against the in-network API.
- Added server audit and safe auto-fix scripts for the Hetzner deployment.
- Added template export/import helpers and extended seeded workflow templates.
- Designed and generated a complete Stepsales template pack.
- Imported the Stepsales template pack into the live Dograh system on Hetzner.
- Added documentation for the next build phase: real sales tools and backend endpoints.

## What is now working
- `sdk` container can be built locally from `sdk-runner/Dockerfile`.
- `api` service is now explicitly started via `./scripts/start_services_dev.sh` in compose to avoid localhost-only binds in some images.
- `sdk` container exports all compatible API env names:
  - `DOGRAH_API_BASE`
  - `DOGRAH_API_ENDPOINT`
  - `DOGRAH_API_URL`
- `python-dotenv` is installed in the `sdk` image, so bundled Python examples run without manual package install.
- Audit script verifies:
  - compose syntax
  - container status
  - `sdk -> api` reachability
  - Docker network attachment
  - local API health
  - cloudflared mode / metrics
  - template table row count
- Auto-fix script repairs known stack issues:
  - missing SDK env vars
  - cloudflared token-mode config
  - SDK network attachment to `dograh-network`

## Live server result
The Stepsales templates were uploaded and imported on the Hetzner server.

Observed result during import:
- `18` template inserts
- SQL transaction committed successfully

Expected UI result:
- Templates should now be available in Dograh under `From templates`.

## Files added / changed
### Stack / deployment
- `README.md`
- `compose.yaml`
- `sdk-runner/Dockerfile`
- `scripts/audit-stack.sh`
- `scripts/apply-stack-fixes.sh`
- `scripts/import-stepsales-templates.sh`
- `scripts/export-workflow-templates.py`
- `scripts/generate-stepsales-template-seed.py`
- `scripts/seed-workflow-templates.sql`

### Stepsales template pack
- `stepsales-templates/stepsales_templates.json`
- `stepsales-templates/stepsales_templates.sql`
- `stepsales-templates/README.md`
- `stepsales-templates/12_tools_setup_guide.md`
- `stepsales-templates/13_sales_api_spec.md`

### Planning / handoff docs
- `docs/superpowers/specs/2026-05-13-stepsales-template-pack-design.md`
- `docs/superpowers/plans/2026-05-13-stepsales-template-pack.md`
- `docs/stepsales-agent-pack/00_master_brief.md`
- `docs/stepsales-agent-pack/01_business_rules.md`
- `docs/stepsales-agent-pack/02_sales_workflows.md`
- `docs/stepsales-agent-pack/03_offer_payment_followup.md`
- `docs/stepsales-agent-pack/04_tools.md`
- `docs/stepsales-agent-pack/05_data_and_crm.md`
- `docs/stepsales-agent-pack/06_knowledge_base.md`
- `docs/stepsales-agent-pack/07_personas_prompts.md`
- `docs/stepsales-agent-pack/08_dograh_template_target.md`
- `docs/stepsales-agent-pack/09_orchestrator_prompt.md`
- `docs/stepsales-agent-pack/10_step_by_step_run_prompts.md`
- `docs/stepsales-agent-pack/11_how_to_use.md`
- `docs/handover/2026-05-13-stepsales-dograh-handover.md`

## Stepsales template pack
### Structure
- `15` motion/persona templates
- `3` complete main templates
- `18` total templates

### Intent
These templates cover a German B2B telesales flow for selling job ad multiposting / additional placements.

### Current limitation
The templates are fully importable and usable in the UI, but several real business actions are still modeled as placeholders rather than real backend operations.

That means the conversation structure exists, but these actions still need real implementation behind them:
- create offer
- send follow-up email
- schedule second call
- send payment link
- check payment status
- mark payment received
- send post-payment information request
- persist call outcome / CRM updates

## Next recommended build phase
Implement the real sales tools and API endpoints described in:
- `stepsales-templates/12_tools_setup_guide.md`
- `stepsales-templates/13_sales_api_spec.md`

Recommended implementation order:
1. `log_call_outcome`
2. `qualify_lead`
3. `send_followup`
4. `create_offer`
5. `schedule_second_call`
6. `send_payment_link`
7. `check_payment_status`
8. `mark_payment_received`
9. `send_post_payment_request`
10. optional `search_jobs`

## Security / hygiene follow-up
These secrets were exposed in chat and should be rotated:
- Dograh API token used for SDK tests
- Cloudflared tunnel token
- SSH key passphrase was also shared in chat context

## Useful operational notes
- `sdk` is a toolbox container, not a CLI binary.
- Direct SDK client auth uses `DOGRAH_API_KEY`.
- Some example scripts accept `DOGRAH_API_TOKEN`, `DOGRAH_API_URL`, or `DOGRAH_API_BASE`.
- If templates do not appear in UI immediately, verify with API or refresh the UI.

## Suggested first step next session
Start implementation of the real backend layer with:
- request / response schemas
- storage model for lead, offer, payment, and follow-up state
- first endpoints: `log_call_outcome` and `qualify_lead`
