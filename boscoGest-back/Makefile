# Variables
DOCKER_COMPOSE = docker-compose
ALEMBIC = alembic
PYTHON = python
CONTAINER_BACK = boscoGest_back
AL_VERSION_DIR_CONTAINER = /app/alembic/versions
AL_VERSION_DIR_HOST = ./alembic/versions

# --- LOCAL MIGRATIONS ---
migrate-local:
	$(ALEMBIC) upgrade head

revision-local:
	$(ALEMBIC) revision --autogenerate -m "$(m)"

downgrade-local:
	$(ALEMBIC) downgrade -1

# --- DOCKER MIGRATIONS ---
migrate-docker:
	$(DOCKER_COMPOSE) exec back alembic upgrade head

revision-docker:
	@echo "Generando revisión dentro del contenedor..."
	$(DOCKER_COMPOSE) exec back alembic revision --autogenerate -m "$(m)"
	@echo "Copiando archivos de 'versions' del contenedor a host..."
	docker cp $(CONTAINER_BACK):$(AL_VERSION_DIR_CONTAINER)/. $(AL_VERSION_DIR_HOST)
	@echo "Revisión copiada correctamente."

downgrade-docker:
	$(DOCKER_COMPOSE) exec back alembic downgrade -1

clean-pyc:
	find . -type d -name "__pycache__" -exec rm -rf {} +
