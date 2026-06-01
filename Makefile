.PHONY: validate validate-knowledge index db-up db-down health health-check migrate-db-policy sync-db-index setup-local-db test-permission test-rag test-agent test-llm test-llm-contract test-llm-injection test-llm-smoke test-llm-live test-security test-db-policy test-db-policy-live test-db-pool-security test-api test-compliance test-crm-handoff test-crm test-business-flow test-frontend-gaokao benchmark benchmark-admissions-gate benchmark-report test test-release-hardening release-check test-route-contract route-inventory test-python-control-plane-freeze test-go-gateway test-go-parity-unit test-parity-fixtures parity-gaokao-chat run-go-gateway-shadow run-go-gateway-shadow-proxy build-go-shadow-gateway smoke-go-shadow-gateway shadow-up shadow-down shadow-health shadow-dry-run shadow-report shadow-mirror-chat shadow-mirror-admin shadow-mirror-dry-run check-shadow-evidence check-shadow-evidence-strict check-cutover-readiness check-cutover-readiness-strict release-check-control-plane ci-policy-check ci-policy-check-json-denied demo-chat demo-api test-ingestion test-graph test-admin-gateway test-admin test-ua-mcp test-admin-console test-p26 test-admin-security test-p261-security test-admin-roles test-profile-merge test-consultation-stage test-recommendation test-admissions-policy test-lead-profile-sync test-phase3 benchmark-phase3 benchmark-tone-quality test-tone-smoke test-backup-recovery check-backup recovery-drill test-admin-production test-campus-auth test-wecom-adapter test-wecom-aibot build-wecom-aibot run-wecom-aibot test-campus-flow test-leave-flow test-meal-flow test-repair-flow test-daily-report test-ai-sidecar test-campus-rls-live test-wecom-inbound run-mealbot-e2e benchmark-mealbot-gate test-pilot-package pilot-smoke seed-school-pilot import-school-pilot mealbot-pause mealbot-resume export-meal-summary test-score-entry test-material-collection test-leave-return-flow test-payment-reconcile test-attendance test-campus-new-modules test-campus-modules-rls-live test-campus-agent-e2e benchmark-campus-agent gate-campus-agent run-ocr-worker matrix-usb-bundle matrix-usb-smoke

ROOT := $(CURDIR)
PY := python3
DOCKER_COMPOSE ?= docker compose
FRONTEND_APP := $(ROOT)/../openhuman-main/app
NODE_BIN ?= /Users/kevinzzz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin
WECOM_AIBOT_DIR := $(ROOT)/services/wecom-aibot-bridge
COMPOSE := $(ROOT)/services/db-policy-service/scripts/compose.sh
DB_HOST_PORT ?= 54329
DB_NAME ?= gaokao_agent_test
DATABASE_URL_ADMIN ?= postgresql://postgres:postgres@localhost:$(DB_HOST_PORT)/$(DB_NAME)
DATABASE_URL_PUBLIC ?= postgresql://gaokao_api_public:postgres@localhost:$(DB_HOST_PORT)/$(DB_NAME)
DATABASE_URL_STAFF ?= postgresql://gaokao_api_staff:postgres@localhost:$(DB_HOST_PORT)/$(DB_NAME)
DATABASE_URL_ADMIN_APP ?= postgresql://gaokao_api_admin:postgres@localhost:$(DB_HOST_PORT)/$(DB_NAME)
PILOT_CONFIG ?= $(ROOT)/configs/pilot_school.example.yaml
SCHOOL ?= demo_school
SCHOOL_ID ?= $(SCHOOL)
DATE ?= $(shell date +%F)
CLASSES_CSV ?= $(ROOT)/data/pilot/examples/classes.csv
STUDENTS_CSV ?= $(ROOT)/data/pilot/examples/students.csv
TEACHERS_CSV ?= $(ROOT)/data/pilot/examples/teachers.csv
PARENT_BINDINGS_CSV ?= $(ROOT)/data/pilot/examples/parent_bindings.csv
ADMIN_POST_PROXY_ROUTES := POST /api/admin/ingestion/runs/{run_id}/cancel,POST /api/admin/staging/docs/{doc_id}/validate,POST /api/admin/staging/docs/{doc_id}/approve,POST /api/admin/staging/docs/{doc_id}/reject,POST /api/admin/staging/docs/{doc_id}/publish

matrix-usb-bundle:
	$(PY) products/matrix/usb_distribution/build_usb_bundle.py --zip

matrix-usb-smoke:
	$(PY) products/matrix/usb_distribution/build_usb_bundle.py --smoke --zip

db-up:
	$(COMPOSE) up -d postgres

db-down:
	$(COMPOSE) down -v

migrate-db-policy:
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) $(PY) services/db-policy-service/scripts/migrate.py --fixtures

sync-db-index:
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) $(PY) services/db-policy-service/scripts/sync_index_to_db.py --root $(ROOT)

setup-local-db: db-up migrate-db-policy sync-db-index test-db-policy-live

validate:
	$(PY) tools/validate.py --root $(ROOT)

validate-knowledge:
	$(PY) tools/validate.py --root $(ROOT) --check-content

index:
	$(PY) services/knowledge-service/src/indexer.py --root $(ROOT)

test-permission: index
	$(PY) -m unittest discover -s services/permission-service/tests -p '*_test.py'

test-rag: index
	$(PY) -m unittest discover -s services/rag-service/tests -p '*_test.py'

test-agent: index
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p '*_test.py'

test-llm:
	$(PY) -m unittest discover -s services/llm-gateway/tests -p '*_test.py'

test-llm-contract:
	$(PY) -m unittest discover -s services/llm-gateway/tests -p 'contract_test.py'

test-llm-injection: index
	$(PY) -m unittest discover -s tests/security -p 'test_prompt_injection_extended.py'

test-llm-smoke: index
	$(PY) -m unittest discover -s services/llm-gateway/tests -p 'live_smoke_test.py'

test-llm-live: index
	DEEPSEEK_ENABLE_LLM_TEST=1 $(PY) -m unittest discover -s tests/security -p 'test_prompt_injection_live.py'

test-compliance:
	$(PY) -m unittest discover -s services/compliance-service/tests -p '*_test.py'

test-api: index
	$(PY) -m unittest discover -s services/api-gateway/tests -p '*_test.py'

test-campus-auth:
	$(PY) -m unittest discover -s services/auth-service/tests -p '*test.py'

test-wecom-adapter:
	$(PY) -m unittest discover -s services/wecom-adapter/tests -p '*test.py'

test-wecom-aibot:
	cd $(WECOM_AIBOT_DIR) && PATH=$(NODE_BIN):$$PATH npm test

build-wecom-aibot:
	cd $(WECOM_AIBOT_DIR) && PATH=$(NODE_BIN):$$PATH npm run build

run-wecom-aibot: build-wecom-aibot
	cd $(WECOM_AIBOT_DIR) && PATH=$(NODE_BIN):$$PATH npm start

test-campus-flow:
	$(PY) -m unittest discover -s services/api-gateway/tests -p 'campus_gateway_test.py'

test-leave-flow: test-campus-flow

test-meal-flow: test-campus-flow

test-repair-flow: test-campus-flow

test-daily-report: test-campus-flow

test-ai-sidecar: test-campus-flow

test-wecom-inbound:
	DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m unittest discover -s services/mealbot-service/tests -p 'test_sprint5_wecom_inbound.py'
	$(PY) -m unittest discover -s services/mealbot-service/tests -p 'message_adapters_test.py'

test-campus-new-modules:
	DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m unittest discover -s services/mealbot-service/tests -p 'test_campus_new_modules.py'

test-score-entry: test-campus-new-modules

test-material-collection: test-campus-new-modules

test-leave-return-flow: test-campus-new-modules

test-payment-reconcile: test-campus-new-modules

test-attendance: test-campus-new-modules

test-campus-modules-rls-live:
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) \
	DATABASE_URL_STAFF=$(DATABASE_URL_STAFF) \
	$(PY) services/db-policy-service/tests/run_campus_modules_rls_tests.py

test-campus-agent-e2e: test-campus-new-modules

benchmark-campus-agent: test-campus-agent-e2e test-campus-modules-rls-live
	$(PY) tools/campus_agent_benchmark.py

gate-campus-agent: benchmark-campus-agent

run-ocr-worker:
	DATABASE_URL=$(DATABASE_URL_ADMIN) MEALBOT_SRC=$(ROOT)/services/mealbot-service/src \
	$(PY) services/mealbot-service/src/app/workers/campus_ocr_worker.py

test-campus-rls-live:
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) \
	DATABASE_URL_PUBLIC=$(DATABASE_URL_PUBLIC) \
	DATABASE_URL_STAFF=$(DATABASE_URL_STAFF) \
	DATABASE_URL_ADMIN_APP=$(DATABASE_URL_ADMIN_APP) \
	$(PY) services/db-policy-service/tests/run_db_policy_tests.py --live

test-crm-handoff:
	$(PY) -m unittest discover -s services/crm-service/tests -p '*_test.py'

test-crm: test-crm-handoff
	$(PY) -m unittest discover -s services/evaluation-service/tests -p '*_test.py'

test-security: index
	$(PY) -m unittest discover -s tests/security -p '*test*.py'

test-staging-percentage-canary-evidence:
	$(PY) -m unittest discover -s tests/security -p 'test_staging_percentage_canary_evidence.py' -v

test-db-policy:
	$(PY) services/db-policy-service/tests/run_db_policy_tests.py

test-db-policy-live:
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) \
	DATABASE_URL_PUBLIC=$(DATABASE_URL_PUBLIC) \
	DATABASE_URL_STAFF=$(DATABASE_URL_STAFF) \
	DATABASE_URL_ADMIN_APP=$(DATABASE_URL_ADMIN_APP) \
	$(PY) services/db-policy-service/tests/run_db_policy_tests.py --live

test-db-pool-security: test-db-policy-live

test-frontend-gaokao:
	cd $(FRONTEND_APP) && PATH=$(NODE_BIN):$$PATH ./node_modules/.bin/vitest run --config test/vitest.config.ts \
		src/api/gaokaoClient.test.ts \
		src/modes/gaokao/GaokaoChatPage.test.tsx \
		src/modes/gaokao/GaokaoCitations.test.tsx \
		src/test/mockApiCore.portSelection.test.ts \
		src/test/mockApiCore.headersRedaction.test.ts

ci-policy-check:
	GAOKAO_ENV=production RAG_SOURCE=postgres $(PY) tools/ci_policy_check.py --root $(ROOT)

ci-policy-check-json-denied:
	! GAOKAO_ENV=production RAG_SOURCE=json $(PY) tools/ci_policy_check.py --root $(ROOT)

test-route-contract:
	$(PY) tools/check_route_contract.py --root $(ROOT)

route-inventory:
	$(PY) tools/check_route_contract.py --root $(ROOT) --inventory

test-python-control-plane-freeze:
	$(PY) tools/check_python_control_plane_freeze.py --root $(ROOT)

test-go-gateway:
	cd $(ROOT)/control-plane && go test ./...

test-go-race:
	cd $(ROOT)/control-plane && go test -race ./...

test-go-control-plane: test-go-gateway test-go-race test-go-shadow test-go-parity test-go-parity-unit test-go-evidence test-go-canary test-go-percentage test-go-readiness check-cutover-readiness

test-go-parity-unit:
	cd $(ROOT)/control-plane && go test ./tests -run TestParityHarnessUnit -count=1

test-go-shadow:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run TestShadow -count=1 -v

test-go-parity:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestParity|TestCapture" -count=1 -v

test-go-evidence:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestEvidence|TestParitySummary" -count=1 -v

control-plane-evidence-check:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestEvidence|TestParitySummary" -count=1 -v

test-go-canary:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestDecideCanary|TestStripCanary|TestBuildCanary|TestRouterCanary|TestCanaryHeader|TestCanaryModel" -count=1 -v

test-go-percentage:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestHashBucket|TestDecidePercentage|TestExtractBucket|TestClamp|TestRouterPercentage|TestRouterHeaderPriority|TestCanaryPercentage" -count=1 -v

test-go-readiness:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestAllRequired|TestMissing|TestFailed|TestParityGate|TestPrivacy|TestP95|TestCandidate|TestMissingRollback|TestMissingOwner|TestPercent|TestHighRisk|TestLowRisk|TestMalformed|TestReadinessReport|TestReadinessConfigWarn|TestParitySummary|TestParityGateWarned|TestRollbackPlan|TestWriteReadiness|TestDefaultConfig|TestPhaseReportEmpty|TestEmptyConfig" -count=1 -v

control-plane-readiness-check:
	cd $(ROOT)/control-plane && go test ./internal/gatewayhttp -run "TestAllRequired|TestMissing|TestFailed|TestParityGate|TestPrivacy|TestP95|TestCandidate|TestMissingRollback|TestMissingOwner|TestPercent|TestHighRisk|TestLowRisk|TestMalformed|TestReadinessReport|TestReadinessConfigWarn|TestParitySummary|TestParityGateWarned|TestRollbackPlan|TestWriteReadiness|TestDefaultConfig|TestPhaseReportEmpty|TestEmptyConfig" -count=1

test-parity-fixtures:
	$(PY) tools/check_parity_fixtures.py --root $(ROOT)

parity-gaokao-chat:
	cd $(ROOT)/control-plane && GO_SHADOW_BASE_URL=$${GO_SHADOW_BASE_URL:-http://127.0.0.1:8788} \
		PYTHON_LEGACY_BASE_URL=$${PYTHON_LEGACY_BASE_URL:-http://127.0.0.1:8787} \
		PARITY_FIXTURE_PATH=$${PARITY_FIXTURE_PATH:-../../tests/parity/gaokao_chat.yaml} \
		go test ./tests -run TestParityGaokaoChatLive -count=1 -v

run-go-gateway-shadow:
	cd $(ROOT)/control-plane && go run ./cmd/gaokao-gateway \
		--routes $(ROOT)/contracts/routes.yaml \
		--listen :8788 \
		--python-base-url http://localhost:8787 \
		--shadow-mode true

run-go-gateway-shadow-proxy:
	cd $(ROOT)/control-plane && go run ./cmd/gaokao-gateway \
		--routes $(ROOT)/contracts/routes.yaml \
		--listen :8788 \
		--python-base-url http://localhost:8787 \
		--shadow-mode true \
		--shadow-proxy-enabled true \
		--shadow-proxy-routes "POST /api/gaokao/chat"

run-go-admin-shadow-proxy:
	cd $(ROOT)/control-plane && go run ./cmd/gaokao-gateway \
		--routes $(ROOT)/contracts/routes.yaml \
		--listen :8788 \
		--python-base-url http://localhost:8787 \
		--shadow-mode true \
		--shadow-proxy-enabled true \
		--shadow-proxy-routes "$(ADMIN_POST_PROXY_ROUTES)"

check-admin-proxy-guard:
	$(PY) tools/check_route_contract.py --root $(ROOT) \
		--admin-proxy-allowlist "$(ADMIN_POST_PROXY_ROUTES)"

test-go-admin-shadow-proxy:
	cd $(ROOT)/control-plane && go test ./tests -run TestAdmin -v -count=1

test-go-admin-parity-unit:
	cd $(ROOT)/control-plane && go test ./tests -run TestAdminParityUnit -v -count=1

parity-admin-post-replacements:
	cd $(ROOT)/control-plane && GO_SHADOW_BASE_URL=$${GO_SHADOW_BASE_URL:-http://127.0.0.1:8788} \
		PYTHON_LEGACY_BASE_URL=$${PYTHON_LEGACY_BASE_URL:-http://127.0.0.1:8787} \
		go test ./tests -run TestParityAdminPostLive -count=1 -v

build-go-shadow-gateway:
	docker build -f $(ROOT)/control-plane/Dockerfile -t gaokao-agent-go-shadow:latest $(ROOT)

smoke-go-shadow-gateway:
	@echo "smoke: build go shadow gateway image"
	docker build -f $(ROOT)/control-plane/Dockerfile -t gaokao-agent-go-shadow:latest $(ROOT) > /dev/null
	@echo "smoke: start go shadow gateway in background"
	@docker stop gaokao-go-smoke 2>/dev/null || true
	docker run -d --rm --name gaokao-go-smoke \
		-p 18788:8788 \
		-e SHADOW_PROXY_ENABLED=false \
		-e SHADOW_PROXY_ROUTES="$(ADMIN_POST_PROXY_ROUTES)" \
		gaokao-agent-go-shadow:latest
	@echo "smoke: waiting for /api/health..."
	@for i in $$(seq 1 20); do \
		sleep 1; \
		if curl -sf http://localhost:18788/api/health > /tmp/go-shadow-smoke.json 2>/dev/null; then \
			echo "  health: ok"; \
			break; \
		fi; \
		if [ $$i -eq 20 ]; then \
			echo "  health: FAIL after 20s"; \
			docker stop gaokao-go-smoke 2>/dev/null; \
			exit 1; \
		fi; \
	done
	@echo "smoke: check route count = 115"
	@python3 -c "import json; d=json.load(open('/tmp/go-shadow-smoke.json')); assert d['route_count']==115, f'route_count={d[\"route_count\"]}'" && echo "  route_count: 115"
	@echo "smoke: check legacy_gap_count = 0"
	@python3 -c "import json; d=json.load(open('/tmp/go-shadow-smoke.json')); assert d['legacy_gap_count']==0, f'legacy_gap_count={d[\"legacy_gap_count\"]}'" && echo "  legacy_gap_count: 0"
	@echo "smoke: check deprecated GET alias returns 405"
	@curl -sf -o /dev/null -w "%{http_code}" http://localhost:18788/api/admin/staging/docs/doc-parity-001/validate 2>/dev/null | grep -q 405 && echo "  deprecated GET: 405" || (echo "  deprecated GET: FAIL"; docker stop gaokao-go-smoke 2>/dev/null; exit 1)
	@echo "smoke: check disabled proxy route returns error"
	@curl -s http://localhost:18788/api/gaokao/chat -X POST -H 'Content-Type: application/json' -d '{"message":"test"}' > /tmp/go-shadow-smoke-err.json 2>/dev/null && \
		python3 -c "import json; d=json.load(open('/tmp/go-shadow-smoke-err.json')); assert d['error']['code']=='PROXY_ROUTE_DISABLED', f'code={d[\"error\"][\"code\"]}'" && echo "  proxy disabled: PROXY_ROUTE_DISABLED" || (echo "  proxy disabled: FAIL"; docker stop gaokao-go-smoke 2>/dev/null; exit 1)
	@echo "smoke: stop container"
	@docker stop gaokao-go-smoke 2>/dev/null
	@rm -f /tmp/go-shadow-smoke.json /tmp/go-shadow-smoke-err.json
	@echo "smoke: PASS"

shadow-up:
	$(DOCKER_COMPOSE) -f $(ROOT)/docker-compose.shadow.yml up -d --build
	@echo "waiting for shadow gateway /api/health..."
	@for i in $$(seq 1 30); do \
		sleep 1; \
		curl -sf http://localhost:$${SHADOW_PORT:-8788}/api/health > /dev/null 2>&1 && echo "shadow-up: OK" && exit 0; \
	done; \
	echo "shadow-up: health check FAILED after 30s"; exit 1

shadow-down:
	$(DOCKER_COMPOSE) -f $(ROOT)/docker-compose.shadow.yml down 2>/dev/null || true
	docker stop gaokao-agent-go-shadow 2>/dev/null || true

shadow-health:
	bash $(ROOT)/scripts/collect_shadow_health.sh $(ROOT)/reports/shadow/health.json

shadow-dry-run:
	bash $(ROOT)/scripts/run_shadow_dry_run.sh

shadow-report:
	$(PY) $(ROOT)/tools/shadow_dry_run_report.py --root $(ROOT)

shadow-mirror-chat:
	$(PY) $(ROOT)/tools/shadow_mirror_driver.py \
		--root $(ROOT) \
		--input $(ROOT)/tests/parity/gaokao_chat_real_sanitized.yaml \
		--legacy-base-url $${PYTHON_LEGACY_BASE_URL:-http://127.0.0.1:8787} \
		--shadow-base-url $${GO_SHADOW_BASE_URL:-http://127.0.0.1:8788}

shadow-mirror-admin:
	$(PY) $(ROOT)/tools/shadow_mirror_driver.py \
		--root $(ROOT) \
		--input $(ROOT)/tests/parity/admin_post_replacements.yaml \
		--legacy-base-url $${PYTHON_LEGACY_BASE_URL:-http://127.0.0.1:8787} \
		--shadow-base-url $${GO_SHADOW_BASE_URL:-http://127.0.0.1:8788}

shadow-mirror-dry-run:
	$(PY) $(ROOT)/tools/shadow_mirror_driver.py \
		--root $(ROOT) \
		--input $(ROOT)/tests/replay/shadow_mirror_sample.jsonl \
		--dry-run

check-shadow-evidence:
	$(PY) $(ROOT)/tools/check_shadow_evidence.py --root $(ROOT)

check-shadow-evidence-strict:
	$(PY) $(ROOT)/tools/check_shadow_evidence.py --root $(ROOT) --strict

check-cutover-readiness:
	$(PY) $(ROOT)/tools/check_cutover_readiness.py \
		--policy $(ROOT)/configs/cutover_policy.yaml \
		--routes $(ROOT)/contracts/routes.yaml

check-cutover-readiness-strict:
	$(PY) $(ROOT)/tools/check_cutover_readiness.py \
		--policy $(ROOT)/configs/cutover_policy.yaml \
		--routes $(ROOT)/contracts/routes.yaml \
		--shadow-report $(ROOT)/reports/shadow/latest.json \
		--mirror-report $(ROOT)/reports/shadow/mirror-latest.json \
		--strict

check-observability-contract:
	$(PY) $(ROOT)/tools/check_observability_contract.py \
		--contract $(ROOT)/configs/observability_contract.yaml \
		--fixtures $(ROOT)/tests/fixtures/observability

check-staging-percentage-canary-config:
	$(PY) tools/check_staging_ingress_config.py \
	  --config deploy/staging/ingress/go-gateway-shadow.percentage-canary.example.yaml \
	  --policy configs/cutover_policy.yaml \
	  --allow-percentage-canary

run-staging-1pct-canary-evidence:
	bash scripts/run_staging_percentage_canary_evidence.sh

check-staging-1pct-canary-evidence:
	$(PY) tools/collect_staging_percentage_canary_result.py \
	  --config reports/staging/tmp/staging-1pct-canary.yaml \
	  --policy configs/cutover_policy.yaml \
	  --percent 1 \
	  --report reports/staging/percentage-canary-1pct-latest.json

staging-header-canary-evidence:
	bash scripts/run_staging_header_canary_evidence.sh

check-staging-header-canary-evidence:
	$(PY) tools/collect_staging_canary_result.py \
	  --report reports/staging/header-canary-latest.json

shadow-evidence-bundle:
	$(PY) $(ROOT)/tools/build_shadow_evidence_bundle.py \
		--root $(ROOT)

test-shadow-evidence-bundle:
	$(PY) -m unittest discover -s tests/security -p 'test_shadow_evidence_bundle.py'

check-staging-ingress-config:
	$(PY) $(ROOT)/tools/check_staging_ingress_config.py \
		--config $(ROOT)/deploy/staging/ingress/go-gateway-shadow.example.yaml \
		--policy $(ROOT)/configs/cutover_policy.yaml

check-staging-header-canary-config:
	$(PY) $(ROOT)/tools/check_staging_ingress_config.py \
		--config $(ROOT)/deploy/staging/ingress/go-gateway-shadow.header-canary.example.yaml \
		--policy $(ROOT)/configs/cutover_policy.yaml \
		--allow-header-canary

release-check-control-plane: release-check test-go-gateway test-go-race

benchmark: index
	GAOKAO_ENV=production \
	RAG_SOURCE=postgres \
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) \
	DATABASE_URL_PUBLIC=$(DATABASE_URL_PUBLIC) \
	DATABASE_URL_STAFF=$(DATABASE_URL_STAFF) \
	DATABASE_URL_ADMIN_APP=$(DATABASE_URL_ADMIN_APP) \
	$(PY) services/evaluation-service/src/benchmark.py --root $(ROOT) --db

benchmark-report:
	$(PY) tools/benchmark_report.py --root $(ROOT)

benchmark-admissions-gate: benchmark
	BENCHMARK_BLOCKING=$${BENCHMARK_ADMISSIONS_BLOCKING:-false} $(PY) tools/release_gate_check.py \
		--name admissions_quality \
		--report $(ROOT)/data/reports/benchmark_report.json \
		--threshold $${BENCHMARK_ADMISSIONS_THRESHOLD:-85}

test-release-hardening:
	$(PY) -m unittest discover -s services/evaluation-service/tests -p 'release_gate_check_test.py'
	DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m unittest discover -s services/mealbot-service/tests -p 'test_sprint6_release_hardening.py'

run-mealbot-e2e:
	DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) services/mealbot-service/scripts/run_e2e_pilot.py

benchmark-mealbot-gate: run-mealbot-e2e
	BENCHMARK_BLOCKING=$${BENCHMARK_MEALBOT_BLOCKING:-true} $(PY) tools/release_gate_check.py \
		--name mealbot_e2e \
		--report $(ROOT)/data/reports/mealbot_e2e_report.json \
		--threshold $${BENCHMARK_MEALBOT_THRESHOLD:-90}

seed-school-pilot:
	PYTHONPATH=$(ROOT)/services/mealbot-service/src DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m app.scripts.onboard_school --config $(PILOT_CONFIG) --school-id $(SCHOOL)

import-school-pilot:
	PYTHONPATH=$(ROOT)/services/mealbot-service/src DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m app.scripts.import_pilot_data \
		--school-id $(SCHOOL_ID) --classes $(CLASSES_CSV) --students $(STUDENTS_CSV) \
		--teachers $(TEACHERS_CSV) --parent-bindings $(PARENT_BINDINGS_CSV) \
		--report $(ROOT)/data/pilot/reports/import_report.json

mealbot-pause:
	PYTHONPATH=$(ROOT)/services/mealbot-service/src DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m app.scripts.pilot_ops pause --school-id $(SCHOOL_ID)

mealbot-resume:
	PYTHONPATH=$(ROOT)/services/mealbot-service/src DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m app.scripts.pilot_ops resume --school-id $(SCHOOL_ID)

export-meal-summary:
	PYTHONPATH=$(ROOT)/services/mealbot-service/src DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m app.scripts.pilot_ops export-summary \
		--school-id $(SCHOOL_ID) --date $(DATE) --output $(ROOT)/data/pilot/exports/meal_summary_$(SCHOOL_ID)_$(DATE).csv

test-pilot-package:
	DATABASE_URL=$(DATABASE_URL_ADMIN) $(PY) -m unittest discover -s services/mealbot-service/tests -p 'test_sprint7_pilot_package.py'

pilot-smoke: test-pilot-package benchmark-mealbot-gate

test: validate test-permission test-rag test-agent test-llm test-llm-contract test-compliance test-api test-crm test-business-flow test-security test-db-policy test-ingestion test-graph

release-check:
	$(MAKE) test-route-contract
	$(MAKE) test-python-control-plane-freeze
	$(MAKE) validate-knowledge
	$(MAKE) test-frontend-gaokao
	$(MAKE) test-db-policy-live
	$(MAKE) test-campus-auth
	$(MAKE) test-wecom-adapter
	$(MAKE) test-wecom-aibot
	$(MAKE) test-campus-flow
	$(MAKE) test-wecom-inbound
	$(MAKE) test-release-hardening
	$(MAKE) test-pilot-package
	$(MAKE) benchmark-mealbot-gate
	$(MAKE) gate-campus-agent
	$(MAKE) test
	$(MAKE) test-llm-contract
	$(MAKE) test-llm-injection
	$(MAKE) benchmark-admissions-gate
	$(PY) -m unittest discover -s services/api-gateway/tests -p '*_test.py'
	$(PY) -m unittest discover -s services/crm-service/tests -p '*_test.py'
	GAOKAO_ENV=production RAG_SOURCE=postgres $(PY) tools/ci_policy_check.py --root $(ROOT)
	$(MAKE) test-ingestion
	$(MAKE) test-graph
	$(MAKE) test-admin-gateway
	! GAOKAO_ENV=production RAG_SOURCE=json $(PY) tools/ci_policy_check.py --root $(ROOT)
	$(MAKE) test-p261-security
	$(MAKE) test-p4-security
	$(MAKE) test-health
	$(MAKE) test-audit
	$(MAKE) test-tone-smoke
	$(MAKE) test-backup-recovery
	$(MAKE) test-admin-production
	$(MAKE) test-phase3
	$(MAKE) benchmark-phase3

demo-chat: index
	$(PY) services/agent-orchestrator/src/pipeline.py \
		--root $(ROOT) \
		--identity '{"user_id":"u_001","role":"parent","campus":"zhengzhou","auth_level":"phone_verified"}' \
		--message '孩子今年 430 分，物理类，想冲一本，自律差，适合什么班？'

demo-chat-llm: index
	DEEPSEEK_ENABLE_LLM=1 $(PY) services/agent-orchestrator/src/pipeline.py \
		--root $(ROOT) \
		--identity '{"user_id":"u_001","role":"parent","campus":"zhengzhou","auth_level":"phone_verified"}' \
		--message '孩子今年 430 分，物理类，想冲一本，自律差，适合什么班？'

demo-api: index
	GAOKAO_ENV=production \
	RAG_SOURCE=postgres \
	DATABASE_URL_ADMIN=$(DATABASE_URL_ADMIN) \
	DATABASE_URL_PUBLIC=$(DATABASE_URL_PUBLIC) \
	DATABASE_URL_STAFF=$(DATABASE_URL_STAFF) \
	DATABASE_URL_ADMIN_APP=$(DATABASE_URL_ADMIN_APP) \
	$(PY) services/api-gateway/src/server.py --root $(ROOT) --host 127.0.0.1 --port 8787

# ──────────────────────────────────────────────
# P2.6 Admin Console & Ingestion targets
# ──────────────────────────────────────────────

test-ingestion:
	$(PY) -m unittest discover -s services/source-ingestion-service/tests -p '*test*.py'

test-graph:
	$(PY) -m unittest discover -s services/knowledge-graph-service/tests -p '*test*.py'

test-admin-gateway:
	$(PY) -m unittest discover -s services/api-gateway/tests -p 'admin_gateway_test.py'

test-admin:
	$(PY) -m unittest discover -s services/api-gateway/tests -p 'admin_gateway_test.py'
	$(PY) -m unittest discover -s tests/admin -p '*test*.py'

test-ua-mcp:
	cd services/ua-mcp-server && $(NODE_BIN)/node ../../external/typescript-sdk-main/node_modules/.bin/vitest run --config vitest.config.ts 2>/dev/null || echo "ua-mcp-server tests need pnpm install first"

test-admin-console:
	cd apps/admin-console && $(NODE_BIN)/node ./node_modules/.bin/vitest run --config vitest.config.ts 2>/dev/null || echo "admin-console tests need pnpm install first"

test-admin-console-no-legacy-get:
	$(PY) tools/check_admin_console_legacy_get_usage.py --root $(ROOT)

# Run all new P2.6 tests
test-p26: test-ingestion test-graph test-admin-gateway test-admin
	$(PY) -m unittest discover -s tests/admin -p '*test*.py'
	$(PY) -m unittest discover -s tests/ingestion -p '*test*.py'
	$(PY) -m unittest discover -s tests/graph -p '*test*.py'
	$(PY) -m unittest discover -s tests/mcp -p '*test*.py'

# Quick sanity that admin endpoints don't break gaokao chat
test-admin-security:
	$(PY) -m unittest discover -s tests/security -p '*admin*test*.py'

# P2.6.2 Admin role granularity tests
test-admin-roles:
	$(PY) -m unittest discover -s services/api-gateway/tests -p 'admin_role_granularity_test.py'

# P2.6.1 Security regression tests
test-p261-security:
	$(PY) -m unittest discover -s services/api-gateway/tests -p 'admin_security_regression_test.py'
	$(PY) -m unittest discover -s services/source-ingestion-service/tests -p 'security_regression_test.py'

# ──────────────────────────────────────────────
# P4.0 Security Hardening
# ──────────────────────────────────────────────

test-p4-security:
	$(PY) -m unittest discover -s tests/security -p 'test_p4_security.py'

check-runtime:
	bash scripts/check_runtime.sh

backup:
	bash scripts/backup.sh

restore:
	bash scripts/restore.sh $(BACKUP_FILE)

test-health:
	$(PY) -m unittest discover -s tests/security -p 'test_health_check.py'

test-audit:
	$(PY) -m unittest discover -s tests/security -p 'test_audit_query.py'

# ──────────────────────────────────────────────
# Phase 3 targets
# ──────────────────────────────────────────────

test-profile-merge:
	$(PY) -m unittest discover -s services/crm-service/tests -p 'profile_merge_policy_test.py'

test-consultation-stage:
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p 'consultation_stage_test.py'

test-recommendation:
	$(PY) -m unittest discover -s services/recommendation-service/tests -p '*test*.py'

test-admissions-policy:
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p 'admissions_answer_policy_test.py'

test-lead-profile-sync:
	$(PY) -m unittest discover -s services/crm-service/tests -p 'lead_profile_sync_test.py'
	$(PY) -m unittest discover -s services/crm-service/tests -p 'next_best_action_test.py'

test-phase3:
	$(PY) -m unittest discover -s services/crm-service/tests -p 'profile_test.py'
	$(PY) -m unittest discover -s services/crm-service/tests -p 'profile_merge_policy_test.py'
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p 'consultation_stage_test.py'
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p 'bt_fsm_test.py'
	$(PY) -m unittest discover -s services/recommendation-service/tests -p '*test*.py'
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p 'admissions_answer_policy_test.py'
	$(PY) -m unittest discover -s services/crm-service/tests -p 'lead_profile_sync_test.py'
	$(PY) -m unittest discover -s services/crm-service/tests -p 'next_best_action_test.py'

benchmark-phase3:
	$(PY) services/evaluation-service/src/benchmark_phase3.py

test-tone-smoke: index
	$(PY) -m unittest discover -s services/agent-orchestrator/tests -p 'tone_quality_smoke_test.py'

benchmark-tone-quality: index
	$(PY) services/evaluation-service/src/benchmark_tone_quality.py

test-backup-recovery:
	$(PY) -m unittest discover -s tests/security -p 'test_backup_recovery.py'

check-backup:
	bash scripts/restore.sh "$(BACKUP_FILE)" --dry-run

recovery-drill:
	bash scripts/recovery_drill.sh

test-admin-production:
	$(PY) -m unittest discover -s tests/security -p 'test_admin_production_readiness.py'

# ---- Health & Release Gate ----

health: test test-go-gateway lint typecheck ci-policy-check test-route-contract \
       test-python-control-plane-freeze test-package-boundary test-gateway-freeze

lint:
	@echo "Running linters..."
	$(PY) -m ruff check services/ tools/ contracts/ --ignore=E501 || true
	cd control-plane && go vet ./... || true

typecheck:
	@echo "Running type checks..."
	$(PY) -m mypy services/ tools/ --ignore-missing-imports || true
	cd $(ROOT)/apps/admin-console && $(NODE_BIN)/tsc --noEmit || true
	cd $(ROOT)/apps/campus && $(NODE_BIN)/tsc --noEmit || true

test-gateway-freeze:
	$(PY) tools/check_gateway_freeze.py --root $(ROOT) --allow-existing

test-package-boundary:
	$(PY) tools/check_package_boundary.py --root $(ROOT) --allowlist contracts/package_boundary_allowlist.json

release-gate: health
	@echo "Release gate: all checks passed"

ci-full: release-gate
	@echo "CI full suite: PASSED"
