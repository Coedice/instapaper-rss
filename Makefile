REMOTE_LOGIN_IDENTIFIER := pi@pi.local
REMOTE_PATH := /home/pi/Documents/instapaper-rss

.PHONY: help
help: ## Show this help message
	@echo "Makefile commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: run
run: ## Run the main program
	uv run python main.py

.PHONY: test
test: ## Run tests
	uv run python test.py

.PHONY: deploy
deploy: ## Deploy to remote server
deploy: format test clean
	ssh-copy-id ${REMOTE_LOGIN_IDENTIFIER}

	# Download pickles from remote
	-scp \
		-r ${REMOTE_LOGIN_IDENTIFIER}:${REMOTE_PATH}/pickles \
		.

	# Deploy
	ssh \
		${REMOTE_LOGIN_IDENTIFIER} \
		'sudo rm -rf ${REMOTE_PATH}'
	scp \
		-r . \
		${REMOTE_LOGIN_IDENTIFIER}:${REMOTE_PATH}

save: ## Save updated sources.yml to git repository
	git pull
	git add config/sources.yml
	git commit -m "Update sources"
	git push

format: ## Format code and sources.yml
	uv run python source_format.py
	uv run isort .
	uv run ruff format

.PHONY: clean
clean: ## Clean up temporary files
	rm -rf __pycache__ .ruff_cache .venv
