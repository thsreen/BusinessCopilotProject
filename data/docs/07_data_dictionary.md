# Data Dictionary

| Field | Type | Example | Description |
|---|---|---|---|
| date | date | 2026-06-15 | Business date |
| order_volume | int | 4250 | Completed orders |
| fulfillment_time_avg | float | 18.5 | Avg hours from order to dispatch |
| fulfillment_time_p95 | float | 42.3 | 95th percentile fulfillment hours |
| return_rate | float | 7.2 | % of orders returned |
| return_volume | int | 306 | Count of returned orders |
| avg_wait_time_min | float | 1.8 | Avg minutes in support queue |
| csat_score | float | 4.3 | Customer satisfaction (1-5) |
| revenue | float | 425000.00 | Total daily revenue |
| units_shipped | int | 6200 | Total units dispatched |
| shipping_cost | float | 31000.00 | Daily carrier costs |
| inventory_accuracy | float | 98.5 | % inventory accuracy |
| category | string | Electronics | Product category |
| warehouse | string | A | Fulfillment center ID |
| channel | string | web | Order/support channel |
