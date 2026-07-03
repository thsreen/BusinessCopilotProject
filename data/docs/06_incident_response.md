# Incident Response

## Severity Classification
| Severity | Definition | Response SLA | Examples |
|---|---|---|---|
| Critical | Revenue impact > $50K or full outage | 15 min | Warehouse fire, payment system down |
| High | Revenue impact $10K-$50K or partial outage | 30 min | Conveyor failure, gateway timeout |
| Medium | Impact < $10K, no customer-facing effect | 2 hours | Inventory discrepancy, minor delays |
| Low | No revenue impact, cosmetic/nuisance | Next business day | Report lag, minor data discrepancy |

## Post-Mortem Requirements
- Critical & High incidents require a post-mortem within 5 business days
- Must include: timeline, root cause, impact, action items, owner
- All post-mortems are stored in the Incident Log repository
