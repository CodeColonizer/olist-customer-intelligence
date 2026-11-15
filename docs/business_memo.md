# Memo: where the marketplace is losing customers, and what to fix first

**To:** Leadership team
**From:** Customer and seller analytics
**Based on:** about 100,000 Olist marketplace orders, September 2016 to August 2018
(detail in the [phase 1](phase1_findings.md), [phase 2](phase2_findings.md),
[phase 3](phase3_findings.md) and [phase 4](phase4_findings.md) findings)

## Bottom line

Growth has stalled and almost nobody comes back. Revenue has been flat at R$0.83m to R$0.98m
a month since early 2018, and only 3% of customers ever order again. The largest problem we
can control is **fulfilment**: orders that arrive late, and orders that arrive on time but
incomplete or wrong. Fix fulfilment first, starting before Black Friday, then invest in
winning customers back.

## What we found

1. **Late delivery is the biggest single driver of bad reviews.** Late orders are 6.8% of
   deliveries but 32.5% of 1-2 star reviews. In the most dissatisfied delivery group, 55% of
   complaints come from customers still waiting for their order, and one in nine says nobody
   replied to them.
2. **"On time" is not the same as "complete".** On-time orders with several items get a 1-2 star
   review 25% of the time, against 7.5% for single items; with several sellers it is 47%. Most
   of these complaints say part of the order never arrived.
3. **A minority of sellers causes a majority of the risk.** Half of established-seller revenue
   sits with underperforming sellers, whose late-dispatch rate is up to 11 times that of the
   best. Complaints about wrong and missing items point to packing problems sellers control.
4. **The value is in customers who are drifting away.** "Lapsing big spenders" are 23% of
   customers but 41% of spend. Customers whose first order arrived within a week return 46%
   more often than those who waited three weeks, so faster delivery also drives retention.
5. **Demand is flat, and November is the next stress test.** We expect about 7,200 items a
   month, and up to 1.6 times that in November if Black Friday repeats 2017. Last November
   the late-delivery rate tripled (from 3.9% to 11.9% of items).

## What we recommend, in priority order

| | Action | Owner | Why | How we'll know it worked |
|---|---|---|---|---|
| 1 | **Make multi-item orders complete and visible:** one tracking number per parcel, "arrives in N packages" at checkout, and "delivered" only when every parcel has arrived | Product, logistics | About 1,540 fewer 1-2 star reviews over the period analysed (12.5% of the total) | Low-review rate on multi-item orders (now 24.6%) |
| 2 | **Get ready for Black Friday:** carrier capacity and seller stock for 1.6x a normal month, and an automatic message with a new date as soon as an order runs late | Logistics, customer service | Last year's peak tripled late deliveries | Late rate in November vs October |
| 3 | **Extend the seller scorecard** with late dispatch and order accuracy (missing or wrong items per 1,000 orders); support high-volume sellers before penalising them | Seller operations | Half of established-seller revenue is at risk | Late-dispatch and accuracy rates by tier |
| 4 | **Tighten proof of delivery** (photo or signature) and add a one-click "not received" claim | Logistics, customer service | 742 customers disputed a recorded delivery in one segment alone | Disputed deliveries per 1,000 orders |
| 5 | **Win back lapsing big spenders,** contacting the customers the repeat-purchase model ranks highest first | CRM | 41% of customer spend | 180-day repeat rate |
| 6 | **Give each category team its specific fix:** packing for furniture and garden tools, supplier quality for electronics and telephony, listing accuracy for textiles and gifts | Category managers | The main complaint differs by category | Complaint rate by category |

Actions 1, 2 and 4 are operational and can start immediately. Action 5 depends on actions 1-3,
because winning customers back is wasted if their next order goes wrong.

## What we are less sure of

- **These are associations, not proven causes.** Pilot before scaling: for example, per-parcel
  tracking in two categories, compared with similar categories that don't have it.
- **Prediction is weak where data is thin.** The repeat-purchase model (AUC 0.58) is good for
  ranking customers, not for individual decisions, and category forecasts are typically 15-27%
  off at one to three months. Plan with the ranges, not single numbers.
- **The data is a public sample ending in August 2018,** and review text covers only customers
  who wrote a comment.

## Suggested next steps

1. Agree owners and baselines for the six measures above, and add them to the Power BI dashboard.
2. Launch the multi-item and proof-of-delivery pilots before November.
3. Re-run this analysis after Black Friday to measure the effect and update the forecasts.
