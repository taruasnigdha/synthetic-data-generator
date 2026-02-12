#!/bin/bash
PROJECT_ID="ai-connect-sap26blr-337"
REGION="us-central1"
SERVICE_NAME="mock-sap-server"

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

echo "Deploying $SERVICE_NAME to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --project $PROJECT_ID \
  --quiet
