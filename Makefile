SHELL := /bin/bash
.PHONY: check-gold audit help install lint test validate-gold download index eval-stage eval-all report demo-offline api-offline up down logs lock

help:           ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ -/'

install:        ## Install dev dependencies
	pip install -r requirements-dev.txt

lint:           ## Lint with ruff
	ruff check .

test:           ## Run unit tests
	python -m pytest -q

validate-gold:  ## Validate the gold question set (structure only)
	python scripts/validate_gold.py

download:       ## Download documents listed in sources.csv
	python scripts/download.py

index:          ## Index documents into Qdrant (incremental). Optional: STAGE=stage3_hybrid
	python scripts/sync_index.py $(if $(STAGE),--stage $(STAGE),)

eval-stage:     ## Run one stage end to end: make eval-stage STAGE=stage2_baseline
	python -m eval.run --stage $(STAGE) --no-threshold --cache-answers $(RUN_ARGS)
	python -m eval.calibrate --stage $(STAGE) $(CAL_ARGS)
	python -m eval.run --stage $(STAGE) --cache-answers $(RUN_ARGS)

check-gold:     ## Check gold evidence is on the stated pages (needs the PDFs in data/raw)
	python scripts/check_gold_evidence.py --ocr

audit:          ## Create the human audit sheet: make audit STAGE=stage4_rerank
	python scripts/audit_sample.py create --stage $(STAGE)

eval-all:       ## Run all stages in order
	for s in stage2_baseline stage3_hybrid stage4_rerank stage5_structure stage6_ocr_tables; do \
	  $(MAKE) eval-stage STAGE=$$s || exit 1; done

report:         ## Build the results table from eval/results
	python -m eval.report --write eval/results/REPORT.md

demo-offline:   ## Permission demo with no API keys (stand-in models, synthetic documents)
	python scripts/demo_offline.py

api-offline:    ## API in offline demo mode (set AUTH_SECRET_KEY first)
	RAG_OFFLINE=1 uvicorn app.api:app --port 8000

up:             ## Start Qdrant, the API and the UI
	docker compose up --build

down:           ## Stop services
	docker compose down

logs:           ## Follow API logs
	docker compose logs -f api

lock:           ## Write an exact dependency lock file
	uv pip compile requirements.txt -o requirements.lock
