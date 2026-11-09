# Power BI dashboard: build guide

This guide builds a four-page dashboard on top of the project's data model. Everything
you need is in the [`powerbi`](../powerbi) folder:

| File | What it is |
|---|---|
| `powerbi/data/*.csv` | the star-schema tables (created by `python scripts/export_powerbi.py`) |
| `powerbi/measures.dax` | all DAX measures, ready to paste |
| `powerbi/theme.json` | colour theme matching the project charts |

Power BI Desktop is free and runs on Windows. No paid licence is needed for anything here.

---

## 1. Load the data

1. **Home → Get data → Text/CSV**, and load each of the 7 files in `powerbi/data/`.
   (Or **Get data → Folder** and combine, but loading individually keeps tables separate.)
2. In **Power Query (Transform data)**, check these data types, then **Close & Apply**:

| Table | Column | Type |
|---|---|---|
| fact_orders | purchase_date | Date |
| fact_orders | items_value, freight_value, order_value, payment_value | Decimal number |
| fact_orders | review_score, is_late, is_delivered, is_low_review | Whole number |
| dim_date | date | Date |
| dim_customers | first_order_date, last_order_date | Date |
| all tables | ID columns (order_id, customer_unique_id, seller_id, product_id) | Text |

3. **View → Themes → Browse for themes**, and select `powerbi/theme.json`.

## 2. Set up the model

**Mark the date table:** select `dim_date` → **Table tools → Mark as date table** → choose `date`.

**Create these relationships** (Model view, drag column to column). All are
many-to-one, single direction, from the dimension to the fact:

| From (one side) | To (many side) |
|---|---|
| dim_date[date] | fact_orders[purchase_date] |
| dim_customers[customer_unique_id] | fact_orders[customer_unique_id] |
| dim_states[state_code] | fact_orders[customer_state] |
| fact_orders[order_id] | fact_order_items[order_id] |
| dim_products[product_id] | fact_order_items[product_id] |
| dim_sellers[seller_id] | fact_order_items[seller_id] |

```
dim_date ─────┐
dim_customers ─┼──▶ fact_orders ───▶ fact_order_items ◀── dim_products
dim_states ───┘                                       ◀── dim_sellers
```

Notes on the design:
- Turn off **auto date/time** (File → Options → Data Load) so Power BI uses `dim_date`.
- Turn off **relationship autodetect** in the same place (Current File → Data Load →
  untick *Autodetect new relationships after data is loaded*). Several columns share
  names across tables (`in_trend_window`, `is_delivered`, `order_status`, `category`),
  and Power BI would otherwise link them automatically. Keep only the six relationships
  above; see [Troubleshooting](#5-troubleshooting).
- `dim_states` links to the order's delivery state. `dim_customers[home_state]` is kept
  as a plain column to avoid two filter paths to the same table.
- Customer segment visuals use `dim_customers`, which holds lifetime figures, so they do
  not respond to the date slicer. Order-level visuals do.

**Sort helpers:** sort `dim_date[month_name]` by `month_number` (Column tools → Sort by column).
The segment and delivery-timing labels start with a number (`1.`, `2.` ...) so they sort
correctly by default.

**Add the measures:** Home → Enter data → name the table `_Measures` → Load. Then
for each block in `measures.dax`, select `_Measures` → **New measure** → paste.
Format `Revenue` and `Average Order Value` as currency (R$), and the rates as percentages.

## 3. Build the pages

**Slicers:** add two separate slicers across the top of each page, one for
`dim_date[year]` and one for `dim_states[region]` (dropdown or tile style). Putting both
fields in a single slicer causes a relationship error. Use **View → Sync slicers** so a
selection carries across all pages.

**KPI cards** (top left of each page), using Revenue as the example:
1. Insert a **Card** visual (or "Card (new)") and add the `Revenue` measure.
2. Select the measure in the Data pane and set **Measure tools → Format** to Currency
   (R$, Portuguese (Brazil)), 0 decimal places. In the card's callout value settings,
   set display units to Millions and 2 decimal places, so it shows R$13.22M.
3. Turn on the title or category label and name it "Revenue".
4. In the new card, add `Revenue YoY %` as a **reference label**, formatted as a
   percentage (1 decimal) with conditional formatting: green above 0, red below.
   It only shows a value when one year is selected; 2018 should show about +145%
   (Jan 1 to Aug 29 in both years, as the data ends on 29 August 2018).
5. Build the other cards the same way, then use **Format painter** to match the styling.

### Page 1: Executive overview

| Visual | Fields |
|---|---|
| 6 KPI cards | Revenue, Delivered Orders, Customers, Average Order Value, Avg Review Score, Late Delivery Rate |
| Line chart | X: dim_date[year_month] · Y: Revenue (filter `in_trend_window` = 1) |
| Bar chart | Y: fact_order_items[category] · X: Item Revenue (Top N filter = 10) |
| Slicers | dim_date[year], dim_states[region] |

**Headline to show:** revenue grew strongly through 2017, then flattened in 2018.

### Page 2: Delivery and satisfaction

| Visual | Fields |
|---|---|
| KPI cards | Late Delivery Rate, Avg Delivery Days, Low Review Rate, Late Share of Low Reviews |
| Column chart | X: fact_orders[delivery_timing] · Y: Low Review Rate |
| Filled map | Location: dim_states[map_location] · Colour saturation: Late Delivery Rate |
| Table | dim_states[state_name], Delivered Orders, Avg Delivery Days, Late Delivery Rate, Avg Review Score |
| **Key influencers** (AI visual) | Analyze: fact_orders[is_low_review] · Explain by: delivery_timing, dim_states[region], primary_payment_type, item_count, freight_value |

**Headline to show:** late orders are under 7% of deliveries but about a third of 1-2 star reviews.
The Key influencers visual should independently surface delivery timing as the top driver,
which is a good talking point: the AI confirms the SQL finding.

### Page 3: Customer segments

| Visual | Fields |
|---|---|
| KPI cards | Segmented Customers, Returning Customer Rate, Customer Spend |
| Clustered bar | Y: dim_customers[cluster_segment] · X: Share of Customers, Share of Customer Spend |
| Clustered bar | Y: dim_customers[rfm_segment] · X: Share of Customers, Share of Customer Spend |
| Matrix (RFM grid) | Rows: r_score · Columns: m_score · Values: Segmented Customers (conditional formatting: background colour) |
| Table | cluster_segment, average of total_spend, recency_days, avg_review_score, avg_delivery_days, avg_installments |

Add a visual-level filter `cluster_segment` is not `No delivered orders` on the segment visuals.

**Headline to show:** lapsing big spenders hold 41% of customer spend, and a "high-value
instalment buyers" group of 16% of customers generates 36% of spend.

### Page 4: Seller scorecard

| Visual | Fields |
|---|---|
| KPI cards | Active Sellers, Item Revenue, Items Sold |
| Scatter chart | Values: dim_sellers[seller_id] · X: late_delivery_rate · Y: avg_review_score · Size: revenue (filter is_established = 1) |
| Table | seller_id, seller_state_name, order_count, revenue, late_delivery_rate, avg_review_score (filter is_established = 1; conditional formatting on late rate and review) |
| Slicer | dim_sellers[seller_region] |

**Headline to show:** sellers with high late rates cluster in the low-review corner of the scatter.

## 4. Publish it to GitHub

Power BI files cannot be previewed on GitHub, so:
1. Save the report as `powerbi/olist_dashboard.pbix`.
2. Take a screenshot of each page and save them as `powerbi/screenshots/page1_overview.png` and so on.
3. Optionally record a 30 to 60 second screen capture (clicking through slicers) and
   upload it as a GIF or link it from the README.

Then add the screenshots to the README.

## 5. Troubleshooting

**"You are using fields that don't have a supported set of relationships"**
Power BI cannot find one clear path between the tables in the visual. Check, in order:
1. Each slicer uses one field only (year and region in separate slicers).
2. In Model view, `dim_date[date] → fact_orders[purchase_date]` and
   `dim_states[state_code] → fact_orders[customer_state]` both exist, are one-to-many
   and single direction, and are drawn as **solid** lines. A dotted line is inactive:
   double-click it and tick *Make this relationship active*.
3. Delete any relationship that is not one of the six in section 2, especially links
   Power BI created automatically on `in_trend_window`, `is_delivered`, `order_status`
   or `category`. Then turn off relationship autodetect (section 2).
4. `fact_orders[purchase_date]` and `dim_date[date]` are both type **Date**, not Text.

**Year-on-year growth looks too low for 2018**
Use the `Revenue PY` and `Revenue YoY %` measures from `measures.dax`, which compare
2018 only with the same months of 2017 (the data ends in August 2018).

**`Revenue YoY %` is blank**
Expected unless exactly one year is selected in the year slicer.
