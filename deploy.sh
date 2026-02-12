#!/bin/bash

source ~/.zshrc

# Load environment variables
if [ -f .env ]; then
  echo "Loading environment variables from .env..."
  source .env
else
  echo "Error: .env file not found."
  exit 1
fi

# Check required variables
REQUIRED_VARS=("PROJECT_ID" "STAGING_BUCKET" "GOOGLE_API_KEY" "AGENT_MODEL" "MOCK_SAP_URL")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "Error: $var is not set in .env"
    exit 1
  fi
done

echo "Deploying Synthetic Data Agent..."
echo "Project ID: $PROJECT_ID"
echo "Staging Bucket: $STAGING_BUCKET"
echo "Agent Model: $AGENT_MODEL"
echo "Mock SAP URL: $MOCK_SAP_URL"

# Deploy using ADK
# Using --project and --region flags explicitly
# Using --env_file .env
adk deploy agent_engine synthetic_data_agent \
  --project "$PROJECT_ID" \
  --region "us-central1" \
  --requirements_file requirements.txt \
  --env_file .env

