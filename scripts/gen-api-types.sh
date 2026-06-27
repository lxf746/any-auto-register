#!/bin/bash
# Generate TypeScript types from the v2 OpenAPI spec.
#
# Usage:
#   1. Start the backend:  python main.py
#   2. Run this script:    bash scripts/gen-api-types.sh
#
# The script fetches the OpenAPI JSON from the running server and uses
# openapi-typescript to produce frontend-new/src/lib/api-types.ts.

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
SPEC_PATH="openapi.json"
OUT_PATH="frontend-new/src/lib/api-types.ts"

echo "Fetching OpenAPI spec from ${BACKEND_URL}/api/v2/openapi.json ..."
curl -sf "${BACKEND_URL}/api/v2/openapi.json" -o "${SPEC_PATH}"

if [ ! -s "${SPEC_PATH}" ]; then
  echo "ERROR: failed to fetch OpenAPI spec" >&2
  exit 1
fi

echo "Generating TypeScript types → ${OUT_PATH}"
npx openapi-typescript "${SPEC_PATH}" -o "${OUT_PATH}"

echo "Done."
