# Databricks layer

Notebooks for the Lakehouse side of ATELIER, run in order. All connections
use `databricks-sql-connector`, not Databricks Connect, because Databricks
Connect is not viable against Serverless compute on the Free Edition.

| Script | Stage |
|---|---|
| `01_bronze_ingestion.py` | Raw ingestion from each source into Bronze |
| `02_silver_transform.py` | Cleaning and conforming into Silver |
| `03_gold_curation.py` | Curated, business-ready Gold entities |
| `04_dlt_pipeline.py` | Delta Live Tables pipeline wiring 01 to 03 together |
| `05_vector_search_setup.py` | Mosaic AI Vector Search index over Gold |
| `06_predictive_models_mlflow.py` | MLflow-tracked demand and pricing models |

Each notebook is self-contained and intended to be uploaded to the
Databricks workspace as-is (Repos or Workspace Files), not executed locally.
