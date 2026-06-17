#!/usr/bin/env bash
# WHAT: copies this package from its extraction location into the project's
#       working folder, creating that folder if it does not yet exist.
# WHY:  keeps the download location (Descargas) separate from the working
#       location (formacion/<project>), the same pattern used for every
#       previous case study in this programme.
# HOW:  run this script from inside the extracted package, with no arguments.
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/home/pruebas/formacion/atelier"

echo "ATELIER demo deployer"
echo "Source: ${SOURCE_DIR}"
echo "Target: ${TARGET_DIR}"

mkdir -p "${TARGET_DIR}"
cp -r "${SOURCE_DIR}/." "${TARGET_DIR}/"

echo "Deployment complete."
echo "Next step: cd ${TARGET_DIR} && cat README.md"
