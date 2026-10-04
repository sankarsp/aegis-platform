#!/usr/bin/env bash
# Builds and ships both tiers to the environment created by infra/terraform.
# Needs: AWS credentials, Docker, Node 22, and `terraform init` already run in infra/terraform.
set -euo pipefail
cd "$(dirname "$0")/.."
ENVIRONMENT="${ENVIRONMENT:-dev}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
TF="terraform -chdir=infra/terraform"

out() { $TF output -raw "$1"; }
REPO=$(out ecr_repository_url)
REGION=$(echo "$REPO" | cut -d. -f4)

echo "1/4 Building and pushing API image $IMAGE_TAG"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${REPO%%/*}"
docker build --platform linux/amd64 -t "$REPO:$IMAGE_TAG" backend
docker push "$REPO:$IMAGE_TAG"

echo "2/4 Rolling out the API (migrations run on container start)"
# Variables come from infra/terraform/terraform.tfvars locally, or TF_VAR_* in CI.
$TF apply -auto-approve -input=false -var "api_image_tag=$IMAGE_TAG" -var "environment=$ENVIRONMENT"
aws ecs wait services-stable --cluster "$(out ecs_cluster)" --services "$(out ecs_service)" --region "$REGION"

echo "3/4 Building the React app"
( cd frontend && npm ci --no-audit --no-fund && \
  VITE_COGNITO_DOMAIN="$(cd .. && out vite_cognito_domain)" VITE_COGNITO_CLIENT_ID="$(cd .. && out vite_cognito_client_id)" npm run build )

echo "4/4 Publishing the app"
aws s3 sync frontend/dist "s3://$(out web_bucket)" --delete --cache-control "public,max-age=31536000,immutable" --exclude index.html
aws s3 cp frontend/dist/index.html "s3://$(out web_bucket)/index.html" --cache-control "no-cache"
aws cloudfront create-invalidation --distribution-id "$(out cloudfront_distribution_id)" --paths "/index.html" >/dev/null

echo "Done: $(out app_url)"
