# Incident Report: Payment Gateway Outage

## Incident ID: INC-2026-004
- Date: July 5, 2026
- Duration: 45 minutes (14:15-15:00 CT)
- Severity: High
- Reported By: Michael Okonkwo (VP Operations)

## Timeline
- 14:15 -- Payment gateway (Stripe) begins returning 429 rate limit errors
- 14:20 -- Transactions failing; checkout blocked for all customers
- 14:25 -- Ops team notified; engineering paged
- 14:35 -- Root cause identified: Stripe rate limit hit due to misconfigured batch processing job
- 14:45 -- Batch job throttled; rate limit restored
- 15:00 -- Full transaction processing restored

## Impact
- 45 minutes of transaction blackout
- ~850 orders delayed
- Revenue impact: ~$85,000 in delayed transactions (all eventually processed)
- No data loss

## Root Cause
A batch reconciliation job was misconfigured to send 10x normal API traffic, hitting Stripe's rate limit. No rate limiting on internal batch job.

## Action Items
1. [Done] Add rate limiting to internal batch jobs
2. [Done] Implement fallback payment gateway (PayPal) as backup
3. [In Progress] Add automatic failover between gateways
4. [Done] Create runbook for payment gateway incidents
