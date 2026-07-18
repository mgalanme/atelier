# CLAUDE.md — atelier

## Qué es

ATELIER. Plataforma de planificación de colecciones de moda construida sobre
Solace Agent Mesh (SAM). Cuatro agentes especialistas coordinados por un
orquestador, con frontend en Streamlit.

## Estado actual: desplegado en producción, funcionando

Arquitectura completa, en la nube, sin dependencia de ninguna máquina local:

```
Streamlit Cloud (frontend)
  └── Railway (contenedor Docker: SAM — OrchestratorAgent + 4 agentes)
        └── Solace Cloud (bróker, orquestación A2A)
              └── Google AI Studio Gemini (LLM, gratuito)
```

- **Cinco componentes SAM**: OrchestratorAgent, TrendAgent, SustainabilityAgent,
  BuyerAgent, StorytellingAgent. Todos confirmados funcionando en producción,
  incluida coordinación multi-agente real (delegación secuencial con
  plan explícito, síntesis final coherente).
- **Databricks Mosaic AI descartado por completo**: los agentes usan
  herramientas Python locales, no Mosaic. No reintroducir Mosaic sin razón
  explícita y documentada.
- **LLM**: Google AI Studio Gemini (`gemini-3.1-flash-lite`), gratuito, sin
  tarjeta. Migrado desde Databricks → Groq → OpenRouter → Gemini a lo largo
  del proyecto; cada cambio fue forzado por límites de cuota o saldo, no por
  preferencia técnica. Ver sección de proveedores LLM más abajo antes de
  volver a cambiar de proveedor.
- **Bróker**: Solace Cloud, servicio `atelier-mesh-v2` (el `-v2` porque el
  primer servicio expiró su trial y hubo que recrearlo; puede volver a pasar).
- **Despliegue backend**: Railway, vía `Dockerfile` en la raíz del repo.
- **Despliegue frontend**: Streamlit Cloud, `streamlit_app/app.py`, con
  `SAM_GATEWAY_URL` como secret apuntando a la URL pública de Railway.

## Gotchas específicos de este repo

### Solace Agent Mesh (SAM 1.26.0)

- `sam init --skip` y `sam add agent --skip` ignoran silenciosamente los
  flags de servicio LLM: usar modo `--gui`.
- El directorio de estado en esta versión de SAM es `.sam/`, no `.solace/`.
- SAM siembra `model_configurations` en `platform.db` una sola vez; para que
  los cambios posteriores en `shared_config.yaml` o en variables del LLM
  surtan efecto **en local** hay que borrar esas filas manualmente:
  ```python
  import sqlite3
  con = sqlite3.connect('platform.db')
  con.execute('DELETE FROM model_configurations')
  con.commit()
  ```
  En Railway no hace falta: el contenedor arranca con SQLite efímero desde
  cero en cada deploy.
- `platform.db` guarda las API keys en texto plano: `.gitignore` debe
  excluir `*.db` y `.sam/`. Comprobar que sigue excluido antes de cualquier
  commit.
- El endpoint WebUI real para clientes propios (no la Web UI de SAM) es
  `POST /api/v1/message:stream` (que activa `is_streaming=True` en el
  contexto de la tarea) seguido de una conexión SSE **separada** a
  `GET /api/v1/sse/subscribe/{task_id}?reconnect=true`. `message:stream` NO
  devuelve el streaming en el cuerpo de esa misma petición; solo confirma
  que la tarea fue aceptada y da el `task_id`. Usar `message:send` en su
  lugar dispara errores `Missing critical info (target_status_topic)`.
- La respuesta final del orquestador puede llegar sin texto visible si el
  LLM decidió no delegar y no generó nada útil en ese turno (no
  determinismo del tool-calling, ver más abajo). No es un bug del cliente;
  reintentar la misma petición suele resolverlo.
- El texto visible del turno final NO siempre está en el evento
  `final_response` (que a menudo solo contiene los embeds resueltos, sin
  texto). Está en los eventos `status_update` de tipo `llm_response`; hay
  que quedarse solo con el **último** turno de ese tipo, no acumular todos
  (el orquestador narra varios turnos intermedios antes de la síntesis
  final, y acumularlos todos produce texto duplicado).
- Artefactos: `GET /api/v1/artifacts/{session_id}` lista, `GET
  /api/v1/artifacts/{session_id}/{filename}` descarga el contenido real
  (branch por `Content-Type` de la respuesta, no asumir JSON).
- El `instruction` del orquestador necesita una regla explícita para
  garantizar que siempre produzca un resumen visible tras delegar, incluso
  en delegaciones a un solo agente; sin ella, el LLM a veces solo emite
  `status_update` embeds y ningún texto final, siguiendo demasiado al pie
  de la letra la instrucción general de "no texto visible durante tool
  calls".

### Proveedores LLM: lecciones de cada migración

- **Databricks Mosaic AI** (primero): rate limit de tokens por minuto muy
  bajo en free tier; se satura solo con el `system_instruction` que SAM
  inyecta (12k-35k tokens de contexto base antes de procesar la petición
  del usuario).
- **Groq**: mismo problema, pero de tokens de **entrada**, no de salida.
  El límite de Groq (12000 TPM para 70b) ya se supera con el contexto base
  de SAM. `MAX_TOKENS` no lo arregla porque ese límite es de salida.
  Groq no es viable para este patrón multi-agente con modelos grandes.
- **OpenRouter**: funcionó bien mientras hubo saldo. Un saldo negativo
  bloquea incluso los modelos `:free`, según su propia documentación. Los
  modelos `:free` de OpenRouter (ej. `llama-3.3-70b-instruct:free`) tienen
  además rate-limiting upstream del proveedor real detrás del modelo
  gratuito (ej. "Venice"), fuera de nuestro control.
- **Google AI Studio Gemini** (actual): gratuito, sin tarjeta, sin saldo que
  gestionar. Tres problemas de configuración a resolver, ya solucionados:
  1. `gemini-2.5-flash` está deprecado para API keys nuevas → usar
     `gemini-3.1-flash-lite` (o el modelo Flash-class vigente; comprobar
     `https://ai.google.dev/gemini-api/docs/models` si vuelve a fallar
     con 404 "no longer available to new users").
  2. Usar el prefijo LiteLLM **nativo** `gemini/`, no `openai/` con
     `api_base` apuntando al endpoint compatible con OpenAI. La ruta
     `openai/` + endpoint compatible falla con `400 Bad Request:
     Function call is missing a thought_signature` en cuanto el
     orquestador encadena dos tool calls seguidas (típicamente al usar
     `save_artifact`, que dispara una llamada interna automática
     `_notify_artifact_save`). Gemini 3.x exige ese campo para
     tool-calling multi-turno; solo el proveedor nativo de LiteLLM lo
     gestiona correctamente.
  3. Con el prefijo nativo `gemini/`, `LLM_SERVICE_ENDPOINT` debe ser
     exactamente `https://generativelanguage.googleapis.com/v1beta`
     (con `/v1beta`, sin `/openai`). Cualquier variante falla con 404:
     sin `/v1beta` falta el segmento de versión que Google exige; con
     `/openai` LiteLLM antepone su propio path y genera una URL con
     `openai` duplicado dentro de la ruta de streaming.
  4. `cache_strategy: "5m"` en `shared_config.yaml` rompe con el
     proveedor nativo `gemini/`: LiteLLM intenta implementarlo vía
     context caching de Vertex AI (`models/{model}:cachedContents`),
     que no está disponible en API keys de tier gratuito de AI Studio.
     Usar `cache_strategy: "none"` para los modelos Gemini.

### Delta / Solace Cloud

- El servicio Solace Cloud "Developer" (free tier) puede expirar su trial;
  si `sam run` da `SOLCLIENT_SUBCODE_UNRESOLVED_HOST`, comprobar primero
  si el servicio sigue existiendo en `console.solace.cloud` antes de
  asumir un problema de red o de credenciales.
- Nunca correr `sam run` en local con el mismo `NAMESPACE` mientras Railway
  esté desplegado y conectado al mismo bróker: ambos compiten por las
  mismas colas durables por agente, y el tier gratuito limita el número
  de clientes por cola (`SOLCLIENT_SUBCODE_MAX_CLIENTS_FOR_QUEUE`).
- Solace PubSub+ Standard en Docker (ya no se usa, pero si se reintroduce)
  necesita `ulimit nofile: soft 2448, hard 1048576`.
- Solace Cloud TLS: la URL `tcps://...` en el puerto 55443 ya activa TLS
  correctamente sin necesitar `without_certificate_validation()` explícito
  en SAM (a diferencia de otros clientes Solace Python usados en proyectos
  anteriores del bootcamp).

### Railway (despliegue del backend)

- El `Dockerfile` va en la **raíz del repo**, y el campo "Dockerfile Path"
  en la configuración de Railway debe ser exactamente `Dockerfile` (no
  `Dockerfile/Dockerfile`, un error fácil de cometer si se usa el
  "Diagnose" automático sin revisar el valor que sugiere).
- El WebUI gateway de SAM arranca en el puerto que Railway inyecta vía la
  variable `PORT` (normalmente `8080`, no `8000`); el `entrypoint.sh` del
  Dockerfile mapea `PORT` a `FASTAPI_PORT` para que SAM lo respete. El
  dominio público generado en Railway debe apuntar a ese mismo puerto real
  (verificar en Settings → Networking, no asumir 8000).
- `platform_service_app` (puerto interno 8001) no necesita exponerse a
  internet: corre en el mismo contenedor que el WebUI gateway y se
  comunican por `localhost` dentro del propio contenedor.

### General

- `ruff check` + `ruff format` antes de cada commit, no después de uno
  fallido.
- `git add -n` para previsualizar antes de un `git add` real.
- No reproducir contenido de handoffs anteriores de memoria sin verificar
  contra el estado real del repo/entorno; varias veces esta sesión un
  supuesto "ya configurado" resultó no serlo (ej. `WEBUI_GATEWAY_ID`
  ausente del `.env`, variables de Railway con nombres de una plantilla de
  Databricks no relacionada con el proyecto).

## Próximos pasos posibles

- Reintento automático en el cliente Streamlit si la respuesta llega vacía
  (mitigación del no determinismo del tool-calling, en vez de depender de
  que el usuario reintente a mano).
- Vigilar los límites de tier gratuito de Gemini (10-15 RPM según modelo)
  bajo uso más intensivo con varios agentes delegando en paralelo.
- Limpiar la rama `railway/fix-deploy-056e64` en GitHub, creada
  automáticamente por una función de diagnóstico de Railway.
