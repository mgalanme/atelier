# ATELIER — Demo Pilot Scaffold

Conversational, agent-orchestrated decision-support platform for the fashion
industry. This package contains the open source, free-tier pilot stack
referenced in the ATELIER Setup Guide (Word document). It does **not**
duplicate the explanatory content of that document: each script and folder
carries only the comments needed to understand the code itself. WHAT, WHY and
HOW for every step live in the Setup Guide.

## Contents

| Folder | Purpose |
|---|---|
| `databricks/` | Bronze, Silver, Gold notebooks, DLT pipeline, Vector Search index, predictive models |
| `agents/` | LangGraph agent logic, Models-as-Code packaging, Mosaic AI registration, HITL orchestrator |
| `solace_mesh/` | Solace Agent Mesh (SAM) configuration: broker, agent YAML files, init script |
| `streamlit_app/` | Conversational front end |
| `scripts/` | Environment validation and lint helpers |

## First run

1. Extract this package to `/home/pruebas/Descargas/atelier-demo-setup` (or
   wherever your downloads land).
2. Run `./deploy.sh` from inside that folder. It creates
   `/home/pruebas/formacion/atelier` and copies everything there.
3. From the target folder, follow the Setup Guide step by step. Do not skip
   ahead: each step assumes only the steps before it.

## Reused from previous case studies

This scaffold reuses the existing Databricks Free Edition workspace, the
existing `mgalanme` GitHub account and PAT authentication already configured
for `gh`, and the operational lessons recorded across the bootcamp (explicit
column lists on Delta MERGE, UUID4 MLflow run IDs, `databricks-sql-connector`
instead of Databricks Connect, `uv` for environments, `ruff` before every
commit). See each folder's own README for specifics.
