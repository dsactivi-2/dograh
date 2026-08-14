# Stepsales Tools Setup Guide

## Purpose

The Stepsales templates are now available in Dograh, but several flows still need real operational tools behind them. This document explains, for each tool, what it should do, what must exist before it can work, and how it should be wired into the overall sales system.

## General Architecture

Each real tool should ideally have:

- a backend endpoint
- input validation
- logging
- status persistence
- predictable JSON output
- failure handling

Recommended technical pattern:

- Dograh workflow calls tool or webhook
- backend endpoint performs the real action
- backend stores result in CRM/order tables
- backend returns structured success/error data

## 1. `log_call_outcome`

### What it does

Stores the result of a call in a structured way.

### Why it matters

This should be the first real tool built because every other process depends on knowing what happened on the call.

### What must exist

- a table or CRM object for call results
- outcome codes
- timestamps
- lead reference

### Recommended fields

- `lead_id`
- `call_id`
- `outcome`
- `summary`
- `interest_level`
- `objection_type`
- `next_step`
- `callback_date`

### Setup steps

1. Create a persistence table or CRM object
2. Define allowed outcome values
3. Build backend endpoint
4. Return stable JSON
5. Add workflow hook/webhook call

### Example use case

After qualification, the agent stores:
- interested
- needs offer
- follow up tomorrow

## 2. `qualify_lead`

### What it does

Creates or updates a lead with qualification data.

### Why it matters

This is the core sales memory layer for the system.

### What must exist

- lead storage
- lead scoring logic
- status field
- next-step field

### Recommended fields

- `company_name`
- `contact_name`
- `role`
- `email`
- `phone`
- `active_hiring`
- `roles_hiring_for`
- `urgency`
- `timeline`
- `budget_signal`
- `interest_level`
- `next_step`

### Setup steps

1. Create lead schema in DB/CRM
2. Define scoring rules
3. Build create-or-update logic
4. Return lead id + score + status
5. Connect from sales workflow

### Example use case

The agent learns:
- 3 open engineering roles
- high urgency
- email confirmed
- wants an offer

The tool saves the lead and marks it as qualified.

## 3. `send_followup`

### What it does

Sends follow-up emails after the call.

### Why it matters

This keeps momentum when the deal does not close live.

### What must exist

- mail infrastructure
- reusable templates
- delivery logging

### Suggested email types

- recap
- case study
- pricing
- product brief
- reminder
- callback confirmation

### Setup steps

1. Connect SMTP or transactional mail provider
2. Create email templates
3. Build endpoint with template selection
4. Store send status
5. Add retry/error path

### Example use case

After a good first call, the agent sends:
- short recap
- offer summary
- next review point

## 4. `create_offer`

### What it does

Creates a commercial offer for the prospect.

### Why it matters

Without a real offer object, the “send offer” flow remains only conversational.

### What must exist

- package catalog
- price table
- discount rules
- document or PDF generation
- offer record storage

### Business rules

- fixed list prices
- max 10 percent discount
- discount reason should be stored

### Setup steps

1. Define package ids and prices
2. Add discount validation
3. Build offer generator
4. Store offer record
5. Optionally generate PDF
6. Link to follow-up mail flow

### Example use case

The agent recommends “Multiposting Paket M”.
The system builds:
- list price
- optional approved discount
- final price
- valid until date

## 5. `schedule_second_call`

### What it does

Books the second commercial conversation.

### Why it matters

The business goal allows a close in the second conversation, so this needs to be a first-class action.

### What must exist

- calendar or scheduling target
- timezone handling
- confirmation output

### Setup steps

1. Choose booking destination
2. Define working hours and slot logic
3. Build scheduling endpoint
4. Send confirmation mail
5. Save appointment state in CRM

### Example use case

The buyer wants to review internally today and talk tomorrow at 10:30.

## 6. `send_payment_link`

### What it does

Creates and sends a payment link after verbal agreement.

### Why it matters

This is the bridge between sales close and money collection.

### What must exist

- payment provider integration
- order or offer reference
- supported methods:
  - direct debit
  - credit card
  - bank transfer

### Setup steps

1. Choose payment provider
2. Map payment methods
3. Build order/payment session creation
4. Generate payment link
5. Send via email or return for immediate delivery

### Example use case

Customer agrees to proceed and wants to pay by card or SEPA.

## 7. `check_payment_status`

### What it does

Checks whether a payment was completed.

### Why it matters

Needed for follow-up, reminders, and post-sale automation.

### What must exist

- payment reference
- provider status sync
- state mapping

### Setup steps

1. Store payment reference
2. Build provider lookup
3. Map provider states to internal states
4. Return normalized payment status

### Example statuses

- pending
- paid
- failed
- canceled
- expired

## 8. `mark_payment_received`

### What it does

Marks a deal/order as paid and activates post-sale flow.

### Why it matters

This is the operational handover from sales to fulfillment.

### What must exist

- order/offer record
- status update logic
- event trigger for onboarding

### Setup steps

1. Build payment confirmation handler
2. Update CRM/order state
3. Trigger post-payment request
4. Log event

## 9. `send_post_payment_request`

### What it does

Sends the structured information request needed to publish the job ad.

### Why it matters

The sales loop is not complete until the fulfillment data is collected.

### What must exist

- email template
- required field checklist
- fulfillment tracking state

### Suggested requested data

- job title
- location
- employment type
- description
- requirements
- benefits
- salary if available
- contact details
- target package / portals

### Setup steps

1. Create required-field checklist
2. Build post-payment email template
3. Add endpoint
4. Save fulfillment request status

## 10. `search_jobs` (optional context tool)

### What it does

Enriches context about job activity.

### Why it matters

Useful for relevance, but should not be the foundation of the sales workflow.

### What must exist

- stable portal integration
- cache
- timeout handling

### Setup guidance

Use only as optional context, never as a hard dependency for the core close path.

## Recommended Build Order

1. `log_call_outcome`
2. `qualify_lead`
3. `send_followup`
4. `create_offer`
5. `schedule_second_call`
6. `send_payment_link`
7. `check_payment_status`
8. `mark_payment_received`
9. `send_post_payment_request`
10. `search_jobs`
