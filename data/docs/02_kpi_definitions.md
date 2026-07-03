# KPI Definitions

| KPI | Formula | Data Source | Refresh |
|---|---|---|---|
| Order Volume | Count of completed orders | Order System | Daily |
| Avg Fulfillment Time (hrs) | Avg(dispatch_time - order_time) per day | Fulfillment System | Daily |
| Fulfillment Time p95 (hrs) | 95th percentile of fulfillment times | Fulfillment System | Daily |
| Return Rate (%) | Returned Orders / Delivered Orders x 100 | Returns System | Daily |
| Return Volume | Count of returned orders | Returns System | Daily |
| Avg Wait Time (min) | Avg time in queue before agent pickup | Contact Center | Daily |
| CSAT Score | Avg survey score (1-5) | Survey System | Daily |
| Revenue ($) | Total order value after discounts | Billing System | Daily |
| Units Shipped | Total item units dispatched | Fulfillment System | Daily |
| Shipping Cost ($) | Total carrier costs | Carrier Billing | Daily |
| Inventory Accuracy (%) | (1 - |variance| / book qty) x 100 | WMS | Weekly |
| On-Time Delivery (%) | Orders delivered by promised date | Carrier Data | Daily |
| Cart Abandonment (%) | Abandoned / Started x 100 | Analytics Platform | Daily |
| CSAT by Channel | CSAT segmented by web/mobile/phone | Survey System | Daily |
| AOV ($) | Revenue / Order Volume | Billing System | Daily |
