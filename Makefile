.DEFAULT_GOAL := test
MANAGE_PY_PATH = python manage.py

.PHONY: requirements update_db random_rentals static help test build pull \
		_build stop run restart attach shell destroy

requirements: ## install development environment requirements
	pip install -q -e ".[dev]"

update_db: ## Install migrations
	$(MANAGE_PY_PATH) migrate

random_rentals: ## Adds random rental operators/listings
	$(MANAGE_PY_PATH) generate_rentals --batch_size=100

static: ## Gather all static assets for production
	$(MANAGE_PY_PATH) collectstatic -v 0 --noinput

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

test: ## Run unit tests for the rentals app
	docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=settings.test web pytest

build: destroy _build

pull:
	docker compose pull

_build:
	find . -type p -delete
	docker compose build

stop:  ## Stop all services
	docker compose stop

dev.up: # Run the server
	docker compose up -d --remove-orphans

restart: # Restart the server
	docker restart rentals.web
	docker restart rentals.db

attach: ## Attach to the django container process to use the debugger & see logs.
	docker attach rentals.web

logs: web-logs ## Run a shell on django container
web-logs: ## Run a shell on the django service container
	docker compose -f docker-compose.yml logs -f --tail=100 web

db-logs: ## Run a shell on the mysql service container
	docker compose -f docker-compose.yml logs -f --tail=100 database

shell: django-shell ## Run a shell on django container
django-shell: ## Run django shell
	docker exec -it rentals.web /bin/bash

db-shell: ## Run mysql shell
	docker exec -it rentals.db /bin/bash

destroy: stop ## Remove all containers, networks, and volumes
	docker compose down -v

# Releasing to PyPI is handled by .github/workflows/release.yaml (trusted
# publishing via OIDC, triggered by pushing a version tag) - there is no
# local/manual publish target. See CONTRIBUTING.md for the release steps.
