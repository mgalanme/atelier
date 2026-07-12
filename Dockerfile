# Dockerfile for the ATELIER SAM mesh (OrchestratorAgent + 4 specialist
# agents + WebUI gateway). Deploys to Railway. The Solace broker itself
# is NOT part of this container: it lives in Solace Cloud, connected to
# via environment variables at runtime.

FROM python:3.12-slim

# System dependencies needed to build some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the exact SAM version confirmed working locally
RUN pip install --no-cache-dir solace-agent-mesh==1.26.0

# Copy only the SAM project directory (configs + src), not the whole
# repo, to keep the image lean and avoid pulling in unrelated bootcamp
# material (databricks/, sql/, other agents).
COPY solace_mesh/sam_project /app/solace_mesh/sam_project

WORKDIR /app/solace_mesh/sam_project

# Railway assigns a dynamic port via the PORT environment variable.
# SAM's WebUI gateway reads its port from FASTAPI_PORT, so this
# entrypoint script bridges the two before starting SAM.
RUN printf '#!/bin/sh\nexport FASTAPI_PORT="${PORT:-8000}"\nexport FASTAPI_HOST=0.0.0.0\nexec sam run\n' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
