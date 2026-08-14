# Stepsales Templates

This folder contains the Stepsales template pack for Dograh.

## Files

- `stepsales_templates.json`  
  Source-of-truth export of all 18 templates with metadata and workflow JSON.

- `stepsales_templates.sql`  
  Generated idempotent SQL seed for inserting the templates into `workflow_templates`.

## What is included

- 15 variant templates
- 3 complete main templates

### Variant templates

- Cold Outreach - Direct SDR
- Cold Outreach - Consultative Advisor
- Cold Outreach - HR Specialist
- Qualification - Direct SDR
- Qualification - Consultative Advisor
- Qualification - HR Specialist
- Demo Booking - Direct SDR
- Demo Booking - Consultative Advisor
- Demo Booking - HR Specialist
- Follow-up - Direct SDR
- Follow-up - Consultative Advisor
- Follow-up - HR Specialist
- Inbound HR Inquiry - Direct SDR
- Inbound HR Inquiry - Consultative Advisor
- Inbound HR Inquiry - HR Specialist

### Main templates

- Stepsales Main - Outbound Qualification to Demo
- Stepsales Main - Outbound Qualification to Follow-up
- Stepsales Main - Inbound HR Conversion Flow

## Regenerate

Run:

```bash
python3 scripts/generate-stepsales-template-seed.py
```

## Import into database

Example:

```bash
psql "$DATABASE_URL" -f stepsales-templates/stepsales_templates.sql
```

Or inside the existing stack, execute the SQL against the same Postgres database used by Dograh.

For the local/self-hosted Dograh compose stack, use:

```bash
chmod +x scripts/import-stepsales-templates.sh
./scripts/import-stepsales-templates.sh
```

## UI availability

Once inserted into `workflow_templates`, the templates should appear in the Dograh UI under the existing “From templates” workflow creation path.
