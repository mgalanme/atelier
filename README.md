# ATELIER — Conversational AI platform for the fashion industry

Agent-orchestrated decision-support platform for fashion collection planning,
built on Solace Agent Mesh (SAM). Part of Martín Galán's agentic AI bootcamp
portfolio.

**Live demo:** Streamlit Cloud app (see repository settings for the current
public URL) — backend runs on Railway, connected to a Solace Cloud broker
and Google AI Studio Gemini.

## Architecture

```
Streamlit Cloud (frontend)
  └── Railway (Docker container: SAM mesh)
        ├── OrchestratorAgent
        ├── TrendAgent
        ├── SustainabilityAgent
        ├── BuyerAgent
        └── StorytellingAgent
              └── Solace Cloud (broker, A2A orchestration)
                    └── Google AI Studio Gemini (LLM)
```

The OrchestratorAgent infers which specialist agent(s) to delegate to from
the user's request, without the user needing to name them explicitly. For
requests spanning multiple domains, it coordinates several agents in
sequence and synthesises their responses into a single coherent answer.

## Contents

| Folder | Purpose |
|---|---|
| `solace_mesh/` | Solace Agent Mesh (SAM) configuration: agent YAML files, shared config, gateway |
| `streamlit_app/` | Streamlit frontend, a thin SSE client over the SAM WebUI gateway |
| `Dockerfile` | Builds the SAM mesh container for Railway deployment |
| `databricks/` | Bronze/Silver/Gold notebooks from an earlier project phase (Mosaic AI, since discarded — see `CLAUDE.md`) |
| `agents/` | LangGraph HITL orchestrator from an earlier project phase (superseded by the SAM mesh) |
| `scripts/` | Environment validation and lint helpers |

Folders `databricks/` and `agents/` reflect an earlier architecture
(Databricks Mosaic AI Model Serving + LangGraph) that was fully replaced by
the current SAM mesh. They remain in the repo as a record of the project's
evolution, not as active components.

## Running locally

Local execution is for development only. **Do not run `sam run` locally
while the Railway deployment is live**: both would compete for the same
durable queues on the shared Solace Cloud broker, and the free tier limits
clients per queue.

```bash
cd solace_mesh/sam_project
source ../../.venv-atelier/bin/activate
sam run
```

Web UI: `http://localhost:8000`.

## Deployment

- **Backend**: Railway, built from the root `Dockerfile`. Environment
  variables (Solace broker credentials, Gemini API key/endpoint, session
  secret) are set in Railway's Variables tab, not committed to the repo.
- **Frontend**: Streamlit Cloud, `streamlit_app/app.py`. `SAM_GATEWAY_URL`
  is set as a Streamlit Cloud secret, pointing to the Railway public URL.

See `CLAUDE.md` for detailed configuration gotchas, provider migration
history, and troubleshooting notes.

## Reused from previous case studies

This project reuses the existing `mgalanme` GitHub account and PAT
authentication already configured for `gh`, and the operational lessons
recorded across the bootcamp (explicit column lists on Delta MERGE, UUID4
MLflow run IDs, `uv` for environments, `ruff` before every commit).
