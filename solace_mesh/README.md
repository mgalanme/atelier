# Solace Agent Mesh (SAM)

Open source orchestration and governance layer, installed from PyPI
(`solace-agent-mesh`) rather than from a Docker image, so that its
configuration files stay under version control alongside the rest of the
project.

| File | Purpose |
|---|---|
| `sam_init.sh` | Wraps `sam init` with the flags this project needs |
| `docker-compose.broker.yml` | Local, free, self-hosted PubSub+ Standard broker |
| `configs/agents/*.yaml` | One entry per specialist agent, each wrapping a Mosaic AI Model Serving endpoint as a SAM tool |

SAM ships with a built-in Orchestrator agent that already breaks an incoming
request down and delegates it to the right specialist agent, which is what
provides the "intelligent routing" described in the architecture document.
The REST API gateway, not the bundled Web UI, is the interface SAM exposes
here, because Streamlit is the conversational front end for this project.

Note: Solace Agent Mesh is an actively evolving open source project. Before
running `sam init`, check `sam init --help` and the current Solace Agent
Mesh documentation for any flag or schema changes since this scaffold was
written.
