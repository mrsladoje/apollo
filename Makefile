PY ?= python3.11
PYTHONPATH := src

HISTORIAN ?= historian.db
INDEX_DIR ?= data/lateon.index
COV_TARGET ?= sim
COV_FAIL_UNDER ?= 85

.PHONY: test test-engine test-plan-b test-plan-c test-gepa regen-golden train-pinn \
        cache-drivers train-ga build-grid build-index plan_b_demo \
        demo-mock backend frontend dev install dryrun-wildcards

install:
	pip install -e ".[dev]"
	cd frontend && npm install

backend:
	PYTHONPATH=src uvicorn apollo.api.app:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Run real backend + frontend together (integrated, no mocks).
dev:
	./scripts/run_dev.sh

demo-mock:
	@echo "Starting Apollo mock demo (mocks-only, zero external deps)..."
	@APOLLO_AGENT=mock APOLLO_TOOLS_BACKEND=mock HISTORIAN_BACKEND=mock RETRIEVAL_BACKEND=mock \
	  PYTHONPATH=src uvicorn apollo.api.app:app --reload --port 8000 &
	@cd frontend && npm run dev

# Plan C §19 — single-command Definition-of-Done sweep.
test-plan-c:
	PYTHONPATH=src $(PY) -m pytest \
	  tests/agent tests/sse tests/eval tests/architecture -q

# Verifies the GEPA artifact + comparison gate (FR-W.10 / FR-W.11).
test-gepa:
	PYTHONPATH=src $(PY) scripts/agent/run_comparison.py --check
	test -f config/agent.system_prompt.gepa.txt
	test -f docs/eval/gepa_compile_log.json

# Live "Ask Apollo" wildcard dry-run (FR-W.5).
dryrun-wildcards:
	PYTHONPATH=src $(PY) scripts/dryrun_wildcards.py

# Default test target — engine only, fast.
test:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m pytest tests/engine -q

test-engine: test

# Plan B test gate — full Plan B suite + coverage threshold (§13.4).
test-plan-b:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m pytest \
	  tests/sim tests/historian tests/policies tests/retrieval tests/counterfactual \
	  --cov=$(COV_TARGET) --cov-report=term-missing \
	  --cov-fail-under=$(COV_FAIL_UNDER) -q

regen-golden:
	PYTHONPATH=$(PYTHONPATH) $(PY) scripts/regen_golden.py

train-pinn:
	PYTHONPATH=$(PYTHONPATH) $(PY) scripts/train_pinn.py

# §6.2 — pre-demo offline driver cache. Run before build-grid.
cache-drivers:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m sim.drivers.cache_all

# §9 — tune AI policy and emit data/ga_fitness.csv + config/policies.yaml.
train-ga:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m sim.optimizer.ga

# FR-2.4 / §8.3 — builds all 9 grid runs into HISTORIAN.
build-grid: cache-drivers
	PYTHONPATH=$(PYTHONPATH) $(PY) -m sim.build_grid

# §12.1 — late-interaction index over the materialized historian.
build-index:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m sim.retrieval.indexer \
	  --historian $(HISTORIAN) --out $(INDEX_DIR)

# §16 demo gate — full Plan B regeneration + Plan B test suite.
plan_b_demo: train-ga build-grid build-index
	@echo "[plan_b_demo] historian.db, lateon.index, ga_fitness.csv, and obituaries regenerated"
	$(MAKE) test-plan-b
