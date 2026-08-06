#!/bin/sh
# Boots n8n with the lead pipeline workflow auto-imported and published, so
# a user never has to build it by hand in the editor. Import/publish must
# happen before `n8n start` -- the CLI writes straight to the DB and n8n
# won't pick up DB changes made while it's already running.
set -e

WORKFLOW_ID="leadpipeline0001"
BCRYPTJS="/usr/local/lib/node_modules/n8n/node_modules/bcryptjs"

# 1. Hash the owner password if a plaintext one was supplied and no
#    pre-hashed value was given directly.
if [ -n "$N8N_OWNER_PASSWORD" ] && [ -z "$N8N_INSTANCE_OWNER_PASSWORD_HASH" ]; then
  export N8N_INSTANCE_OWNER_PASSWORD_HASH="$(
    node -e "console.log(require('$BCRYPTJS').hashSync(process.env.N8N_OWNER_PASSWORD, 10))"
  )"
fi
export N8N_INSTANCE_OWNER_MANAGED_BY_ENV=true
export N8N_INSTANCE_OWNER_EMAIL="${N8N_OWNER_EMAIL:-owner@example.com}"
export N8N_INSTANCE_OWNER_FIRST_NAME="${N8N_INSTANCE_OWNER_FIRST_NAME:-Lead}"
export N8N_INSTANCE_OWNER_LAST_NAME="${N8N_INSTANCE_OWNER_LAST_NAME:-Admin}"

# 2. Import + publish the shipped workflow, unless it's already present
#    (so edits made in the n8n UI survive container restarts) or the user
#    explicitly asked to reset it.
NEEDS_IMPORT=false
if [ "$N8N_FORCE_REIMPORT" = "true" ]; then
  NEEDS_IMPORT=true
elif ! n8n export:workflow --id="$WORKFLOW_ID" --output=/tmp/existing-workflow-probe.json >/tmp/probe.log 2>&1; then
  NEEDS_IMPORT=true
fi

if [ "$NEEDS_IMPORT" = "true" ]; then
  echo "Importing bundled lead pipeline workflow..."
  n8n import:workflow --input=/workflows/lead-pipeline.json
  n8n publish:workflow --id="$WORKFLOW_ID"
else
  echo "Lead pipeline workflow already present, skipping import (set N8N_FORCE_REIMPORT=true to reset it)."
fi

exec n8n start
