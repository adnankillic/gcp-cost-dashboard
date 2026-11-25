# GCP Cost Dashboard

A Streamlit dashboard for Google Cloud costs. It has two pages:

- **GCP All Services**: net cost and credits by service, SKU, project and region
- **BigQuery**: query cost by user and statement type, plus the most expensive queries

Each page has a Daily / Monthly switch and filters in the sidebar.

## Data

The dashboard uses **sample data** for August to October 2026. The data is
modeled on a real GCP cost pipeline (GCP billing export and BigQuery job
metadata), but it is not real spend:

- All cost and usage numbers are scaled and changed with random daily noise
- User emails are replaced with aliases (`analyst_01`, `sa_etl_compute`, ...)
- Project names are replaced with aliases (`data-platform`, `game_01`, ...)
- Query text is replaced with a sample query for each statement type
- Job ids are hashed

The trends and the shape of the data are close to a real setup, so the charts
behave like they would in production.

| File | Grain |
|---|---|
| `data/gcp_cost_daily.csv` | day x service x SKU x project x region |
| `data/bq_cost_daily.csv` | day x user x statement type |
| `data/bq_top_jobs.csv` | top 500 jobs by cost |

## Daily cost alerts (production setup)

In production, this dashboard is not the only check. An n8n workflow runs every
morning and sends a cost report by email and Slack. There are two reports, one
for BigQuery and one for all GCP services.

Each report shows the last 7 days and compares every day with the day before.

- **BigQuery:** a day is flagged if the cost is more than 50% higher than the
  day before. Days that are not finished yet are not compared.
- **GCP all services:** a day is flagged if the net cost is 30% or more higher
  than the day before. The billing export can be late, so recent days are marked
  as partial or "late records possible". A partial day is only flagged if it is
  already over the 30% limit.

If a day is flagged, the report shows a warning at the top, so the problem can
be checked the same day.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
app.py            # page navigation
common.py         # data loading, filters, chart helpers
views/gcp.py      # GCP All Services page
views/bigquery.py # BigQuery page
data/             # anonymized CSV files
```
