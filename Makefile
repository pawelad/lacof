# Source: http://clarkgrubb.com/makefile-style-guide
MAKEFLAGS += --warn-undefined-variables
.DEFAULT_GOAL := help

PIP_COMPILE = CUSTOM_COMPILE_COMMAND='make pip-compile' python -m piptools compile \
	--resolver=backtracking \
	--allow-unsafe \
	--strip-extras \
	--quiet

.PHONY: install
install: ## Install app dependencies
	python -m pip install pip-tools -c requirements/constraints.txt
	python -m piptools sync --pip-args "--no-deps" requirements/main.txt

.PHONY: install-dev
install-dev: ## Install app dependencies (including dev)
	python -m pip install pip-tools -c requirements/constraints.txt
	python -m piptools sync --pip-args "--no-deps" requirements/main.txt requirements/dev.txt

.PHONY: pip-compile
pip-compile: ## Compile requirements files
	@$(PIP_COMPILE) --generate-hashes requirements/main.in
	@$(PIP_COMPILE) --generate-hashes requirements/dev.in
	@$(PIP_COMPILE) --output-file requirements/constraints.txt requirements/main.txt requirements/dev.txt

.PHONY: upgrade-package
upgrade-package: ## Upgrade Python package (pass "package=<PACKAGE_NAME>")
	@$(PIP_COMPILE) --generate-hashes --upgrade-package $(package) requirements/main.in
	@$(PIP_COMPILE) --generate-hashes --upgrade-package $(package) requirements/dev.in
	@$(PIP_COMPILE) --output-file requirements/constraints.txt requirements/main.txt requirements/dev.txt

.PHONY: upgrade-all
upgrade-all: ## Upgrade all Python packages
	@$(PIP_COMPILE) --generate-hashes --upgrade requirements/main.in
	@$(PIP_COMPILE) --generate-hashes --upgrade requirements/dev.in
	@$(PIP_COMPILE) --output-file requirements/constraints.txt requirements/main.txt requirements/dev.txt

.PHONY: run
run: ## Run the app
	gunicorn --pythonpath=src --worker-class=uvicorn.workers.UvicornWorker --reload lacof.app

.PHONY: format
format: ## Format code
	black src/ tests/ noxfile.py
	isort src/ tests/ noxfile.py
	ruff check --fix src/ tests/ noxfile.py

.PHONY: test
test: ## Run the test suite
	nox

.PHONY: clean
clean: ## Clean dev artifacts
	rm -rf .mypy_cache/ .nox/ .pytest_cache/ .ruff_cache/

# Source: https://www.client9.com/self-documenting-makefiles/
.PHONY: help
help: ## Show help message
	@awk -F ':|##' '/^[^\t].+?:.*?##/ {\
	printf "\033[36m%-40s\033[0m %s\n", $$1, $$NF \
	}' $(MAKEFILE_LIST)
