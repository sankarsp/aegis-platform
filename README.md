# Aegis: data and AI governance for fintechs

Aegis is one control plane for a fintech's data and AI governance: lineage to regulatory reports, data quality with
filing gates, a catalog of owners and business terms, access and privacy controls, recertification campaigns, an
AI model inventory with fairness, drift and generative AI monitoring, and coverage of every payment rail the
business runs (ACH, wires, Fedwire, Swift, RTP, FedNow and SEPA Instant). Every action lands in a hash-chained audit log.

| Tier | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, React Router |
| API | FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Database and vector store | PostgreSQL 16 with pgvector (Aurora PostgreSQL Serverless v2 in AWS) |
| Embeddings | Amazon Bedrock Titan Text Embeddings v2 (1,024 dimensions) |
| Sign-in | Amazon Cognito hosted UI, authorization code flow with PKCE, MFA required |
| Hosting | S3 and CloudFront for the app; ECS Fargate behind an internal ALB for the API |
| Infrastructure | Terraform (AWS provider 5.82 or later) |

## Architecture

```mermaid
flowchart LR
  user[Browser] -->|HTTPS| cf[CloudFront]
  cf -->|static files| s3[(S3: React build)]
  cf -->|/api/* via VPC origin| alb[Internal ALB]
  user -->|sign in| cognito[Cognito hosted UI]
  subgraph VPC [VPC, private subnets]
    alb --> ecs[ECS Fargate: FastAPI]
    ecs --> aurora[(Aurora PostgreSQL + pgvector)]
    ecs -->|VPC endpoint| bedrock[Bedrock: Titan embeddings]
  end
  ecs -. verifies ID token .-> cognito
```

The API has no public endpoint: the ALB is internal, and CloudFront reaches it through a VPC origin (network interfaces
CloudFront places inside the VPC). Aurora is encrypted with a customer-managed KMS key and forces TLS. RDS generates and
rotates the master password in Secrets Manager; the API reads it when it opens a connection, so rotation needs no restart.
Concurrent tasks are safe on first start: migrations, demo seeding and audit-log appends each take a PostgreSQL advisory lock.

### What the vector store does

Every governed object (datasets, CDEs, glossary terms, policies, reports, model cards and steward-confirmed column
labels) is embedded into the `knowledge_vectors` table with an HNSW cosine index. It powers:

- **Ask Aegis** (`POST /api/ask`, `GET /api/search`): semantic search across all governance records. If
  `AEGIS_BEDROCK_CHAT_MODEL_ID` is set, a Bedrock model also drafts a short answer that cites only the retrieved records.
- **Duplicate term check** (`GET /api/catalog/glossary/similar`): finds existing glossary terms before a steward adds a new one.
- **Label suggestions** (`POST /api/access/suggest-classification`): proposes a sensitivity label for a new column from
  the nearest steward-confirmed columns. Suggestions are advisory; a steward confirms every label.

The index is rebuilt after changes that affect it and can be rebuilt on demand with `POST /api/admin/reindex`.

## Payment rails

The Payment rails page shows each payment type with its operator, message standard, settlement, limits, the rules
that apply and dated rule changes (in effect or upcoming). Each rail is tied to its critical data elements, the
quality rules on them, open issues, the fraud and AML models that score it, and the Travel Rule recordkeeping lineage.

| Rail | Example rules and checks in the demo data |
| --- | --- |
| ACH | Nacha 2026 fraud monitoring and PAYROLL / PURCHASE descriptions; SEC code validity; unauthorized returns against Nacha's 0.5% |
| Wire transfers | Product that routes to Fedwire or Swift; Travel Rule data on transfers of $3,000 or more; UCC 4A |
| Fedwire Funds | ISO 20022 since 14 Jul 2025; structured address quality |
| Swift cross-border | CBPR+ after the end of MT coexistence; UETR on every payment; unstructured address retirement (deferred, date due by December 2026) |
| RTP and FedNow | $10 million network limits; end-to-end ID uniqueness; real-time fraud scoring |
| Instant Payment (SEPA Inst) | EU Instant Payments Regulation: Verification of Payee before authorisation, daily customer sanctions screening |

Rail reference data lives in `backend/app/payments.py`. On start-up Aegis adds it to databases seeded by an older
release and refreshes rules, limits and dated changes on existing ones without touching metrics. Rule-change dates
were checked in October 2026; volumes and quality results are examples.

## Run it locally

**With Docker** (PostgreSQL with pgvector, API and app):

```bash
docker compose up --build
# app: http://localhost:8080   API docs: http://localhost:8000/docs
```

**Without Docker** (SQLite and an in-memory vector store, fastest for UI work):

```bash
cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev        # http://localhost:5173
```

Locally there is no sign-in: the API acts as `AEGIS_DEV_USER` (default "Priya Nair") with every role, or as the
person named in an `X-User` header. Offline runs use a deterministic hashing embedder (`AEGIS_EMBEDDING_PROVIDER=hash`), which matches on shared
words rather than meaning; set `AEGIS_EMBEDDING_PROVIDER=bedrock` with AWS credentials for real semantic search.

The database starts with demo data for Northwind Pay, a fictional fintech. Set `AEGIS_SEED_DEMO_DATA=false` for real tenants.

## Tests

```bash
cd backend
pytest                                                    # SQLite + in-memory vectors
AEGIS_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aegis_test pytest   # PostgreSQL + pgvector
```

The suite covers the governance rules end to end: lineage sign-off and completeness, impact analysis, quality gates
holding a report until its issue is resolved, orphaned-owner reassignment, vector search and label suggestions,
recertification decisions and sealing, AI fairness mitigation with re-approval by different people, the model kill
switch, roles, evidence packs, audit-chain tamper detection, and Cognito token rejection. CI runs it against both databases.

## Deploy to AWS

Prerequisites: Terraform 1.6+, AWS CLI, Docker, Node 22, and access to Titan Text Embeddings v2 enabled in the
Bedrock console for your region.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars      # set cognito_domain_prefix and demo_reviewer_email
cp backend.hcl.example backend.hcl                # your S3 state bucket and DynamoDB lock table
terraform init -backend-config=backend.hcl
terraform apply -target=aws_ecr_repository.api    # first time only: the registry must exist before the first image
cd ../.. && ./scripts/deploy.sh                    # builds and pushes the API, applies Terraform, publishes the app
```

`deploy.sh` prints the app URL. Users are created by an admin; they set a password and an authenticator app on
first sign-in:

```bash
aws cognito-idp admin-create-user --user-pool-id <pool id> --username priya@yourfirm.com \
  --user-attributes Name=email,Value=priya@yourfirm.com Name=email_verified,Value=true Name=name,Value="Priya Nair"
aws cognito-idp admin-add-user-to-group --user-pool-id <pool id> --username priya@yourfirm.com --group-name aegis-steward
```

Identity is the verified email address. Roles come from Cognito groups:

| Group | Can |
| --- | --- |
| (none) | Read everything, answer their own review items, generate evidence packs |
| `aegis-steward` | Sign off lineage hops, resolve issues, confirm labels, run quality and AI tests, assign owners, approve glossary changes |
| `aegis-approver` | Record model approval steps, pause or resume models, seal campaigns |
| `aegis-admin` | Change access policies, rebuild the search index, seal campaigns |

Each model approval step must be signed by a different person, and a paused model cannot be re-versioned or approved
until it is resumed. With demo data on, the sample review items go to `demo_reviewer_email`.

Pushes to `main` deploy automatically once the repository variables `AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`,
`TF_STATE_BUCKET`, `TF_LOCK_TABLE` and `COGNITO_DOMAIN_PREFIX` are set (see the deploy job in `.github/workflows/ci.yml`).

Before holding real data: keep `deletion_protection = true`, configure an S3 backend for Terraform state, add a custom
domain with an ACM certificate to CloudFront, attach AWS WAF to the distribution, and federate Cognito with the
client's identity provider.

## API

Interactive docs are at `/docs`. Main routes:

| Area | Routes |
| --- | --- |
| Overview | `GET /api/overview`, `GET /api/audit`, `GET /api/me` |
| Lineage | `GET /api/reports`, `GET /api/reports/{id}`, `POST /api/reports/{id}/edges/{edge}/signoff`, `GET /api/reports/{id}/nodes/{node}/impact`, `POST /api/reports/{id}/evidence-pack` |
| Data quality | `GET /api/quality/rules`, `POST /api/quality/run`, `GET /api/quality/issues`, `POST /api/quality/issues/{id}/resolve`, `GET /api/quality/gates` |
| Catalog | `GET /api/catalog/assets`, `POST /api/catalog/assets/{id}/owner`, `GET /api/catalog/cdes`, `GET /api/catalog/glossary`, `GET /api/catalog/glossary/similar`, `POST /api/catalog/glossary/{id}/approve` |
| Access and privacy | `GET /api/access/scans`, `POST /api/access/scans/{id}`, `POST /api/access/suggest-classification`, `GET /api/access/policies`, `POST /api/access/policies/{id}/toggle` |
| Recertification | `GET /api/recert/campaigns`, `GET /api/recert/inbox`, `POST /api/recert/items/{id}/decision`, `POST /api/recert/campaigns/{id}/seal`, `GET /api/recert/tasks` |
| AI governance | `GET /api/ai/models`, `GET /api/ai/models/{id}`, `POST /api/ai/models/{id}/fairness-test`, `.../mitigate`, `.../evaluate`, `.../approve`, `.../pause`, `.../revalidate` |
| Payment rails | `GET /api/payments/rails`, `GET /api/payments/rails/{id}` |
| Search | `GET /api/search`, `POST /api/ask`, `POST /api/admin/reindex` |

## What is simulated in this MVP

These parts have working interfaces but stand-in implementations, so the console runs without client systems:

- **Rule execution.** `SimulatedRuleRunner` nudges results; replace it with a runner that pushes SQL down to the
  client's warehouse (Snowflake, Redshift, Databricks).
- **Lineage harvesting.** Lineage is seeded; production ingests OpenLineage events and parses dbt manifests and SQL logs.
- **Classification scans, fairness tests and generative AI evaluations.** Results are seeded and re-scored with small
  random changes; production reads the scanner output, the decision log and the evaluation harness.
- **Policy enforcement.** Policies toggle in Aegis; production compiles them to masking policies and grants in each platform.
- **Recertification campaigns.** Progress from reviewers outside the demo user is a stored count.

## Repository layout

```
backend/    FastAPI app, Alembic migrations, tests
frontend/   React app (Vite)
infra/      Terraform for AWS
scripts/    deploy.sh
```
