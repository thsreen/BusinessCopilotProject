# Incident Report: Mobile App v3.2 Regression

## Incident ID: INC-2026-003
- Date Detected: April 1, 2026
- Severity: High
- Reported By: Priya Sharma (VP Engineering)

## Timeline
- Mar 30 -- Mobile app v3.2 deployed to production (100% rollout)
- Apr 1 -- CSAT on mobile channel drops from 4.3 to 3.7
- Apr 2 -- Cart abandonment on mobile increases from 68% to 78%
- Apr 3 -- Root cause identified: cart timeout reduced from 30min to 10min (too aggressive)
- Apr 4 -- Hotfix v3.2.1 developed, tested
- Apr 10 -- Hotfix deployed (delayed due to testing -- cautious approach after previous incidents)
- Apr 12 -- Mobile CSAT recovering to 4.0
- Apr 18 -- Mobile CSAT fully recovered to 4.3

## Impact
- CSAT drop: 4.3 -> 3.7 on mobile (lowest channel score ever)
- Cart abandonment: 68% -> 78% on mobile
- Estimated revenue impact: $45,000 (lost carts over 10 days)
- Overall CSAT affected: 4.2 -> 3.8 (company-wide low)

## Root Cause
Product decision to reduce cart timeout from 30min to 10min to reduce inventory holds, without sufficient user testing. No gradual rollout or A/B testing performed.

## Action Items
1. [Done] Rollback to 30min timeout via hotfix v3.2.1
2. [Done] Add A/B testing requirement to deployment pipeline
3. [In Progress] Create feature flag system for gradual rollouts
4. [Done] Update deployment checklist to include CSAT monitoring
