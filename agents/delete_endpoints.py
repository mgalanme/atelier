"""
Elimina todos los endpoints de Model Serving que empiecen por "atelier-"
(excepto "atelier-agents" si existiera) para liberar cuota en Free Edition.
"""

from databricks.sdk import WorkspaceClient

client = WorkspaceClient()

endpoints_to_keep = {"atelier-agents"}  # No eliminar este si ya existe

for endpoint in client.serving_endpoints.list():
    name = endpoint.name
    if name.startswith("atelier-") and name not in endpoints_to_keep:
        print(f"Deleting endpoint: {name}")
        client.serving_endpoints.delete(name=name)
    else:
        print(f"Skipping endpoint: {name}")
print("Cleanup completed.")
