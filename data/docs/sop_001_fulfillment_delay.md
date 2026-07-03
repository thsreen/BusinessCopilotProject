# SOP-001: Fulfillment Delay Handling
Version: 2.1 | Last Updated: 2025-12-01

## Purpose
Ensure consistent handling when fulfillment times exceed targets.

## Triggers
- Avg fulfillment time > 30 hours on any day
- p95 fulfillment time > 55 hours on any day
- Any warehouse exceeds 36 hours avg

## Procedure
1. **Identify bottleneck** (within 1 hour of breach):
   - Check picking vs packing vs carrier pickup times
   - Use fulfillment system dashboard
2. **Alert Warehouse Lead** immediately
3. **If > 36 hrs avg**: Trigger Tier-1 escalation via escalation tool
4. **Communicate**: Update estimated delivery dates for affected orders
5. **Log**: File root cause in incident tracker within 24 hours
6. **Follow-up**: Review within 48 hours to confirm resolution

## Escalation Criteria
| Condition | Escalation Level |
|---|---|
| Single warehouse, single day > 36 hrs | Tier-1 |
| Same warehouse, 2+ consecutive days > 36 hrs | Tier-2 |
| Multiple warehouses, same day > 36 hrs | Tier-2 |
| Any warehouse > 48 hrs | Tier-3 |
