# Incident Report: Inventory Count Discrepancy -- Home & Garden

## Incident ID: INC-2026-005
- Date Detected: August 1, 2026
- Severity: Medium
- Reported By: David Kim (Director of Fulfillment)

## Timeline
- Jul 28 -- Weekly cycle count skipped at Warehouse B due to staffing shortage
- Jul 31 -- Customer reports ordered "Garden Tool Set" received wrong item
- Aug 1 -- Full audit of Home & Garden category at Warehouse B
- Aug 1 -- 8% inventory variance found (worst in: garden tools, patio furniture)
- Aug 2 -- Correction entries applied to WMS
- Aug 3 -- Mandatory weekly cycle count policy re-emphasized

## Impact
- 8% inventory accuracy in Home & Garden at Warehouse B
- ~120 incorrect shipments to customers over ~2 weeks
- Estimated cost of return/refill: $4,500
- No revenue loss (all customers either got correct item or received refund)

## Root Cause
Cycle count process skipped due to staffing. No automated alert when counts are missed. Inventory drifted as pickers corrected errors in system without verification.

## Action Items
1. [Done] Full reconciliation of Home & Garden category
2. [Done] Mandatory weekly cycle counts reinstated
3. [In Progress] Add automated alerts when cycle counts are missed
4. [Planned] Implement cycle count compliance dashboard
