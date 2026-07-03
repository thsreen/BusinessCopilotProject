# Compliance Policies

## Data Handling
- PII (personally identifiable information) must never be stored in logs
- Customer names, emails, addresses, and payment data must be masked in any output
- Log retention: 90 days for operational logs, 7 years for financial records

## Audit Trail
- All modifications to KPI definitions or SLA thresholds must be logged with user ID and timestamp
- Weekly compliance review checklists must be filed by EOD each Friday

## Security
- API keys and secrets must use environment variables or a secrets manager
- No credentials in code, config files, or documentation
- Access to operations data is read-only for analysts
