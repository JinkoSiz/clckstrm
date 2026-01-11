.PHONY: help build up down restart logs ps clean test lint format migrate generate-csv start-generator

# Переменные
COMPOSE = docker-compose
BACKEND_CONTAINER = backend
GENERATOR_CONTAINER = generator

# Цвета для вывода
GREEN = \033[0;32m
NC = \033[0m

help: ## Показать справку
	@echo "Clickstream Analytics - Makefile команды"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Docker Compose команды
# =============================================================================

build: ## Собрать все Docker образы
	$(COMPOSE) build

up: ## Запустить все сервисы
	$(COMPOSE) up -d

up-logs: ## Запустить все сервисы с логами
	$(COMPOSE) up

down: ## Остановить все сервисы
	$(COMPOSE) down

restart: ## Перезапустить все сервисы
	$(COMPOSE) restart

logs: ## Показать логи всех сервисов
	$(COMPOSE) logs -f

logs-backend: ## Показать логи backend
	$(COMPOSE) logs -f backend

logs-kafka: ## Показать логи Kafka
	$(COMPOSE) logs -f kafka-1 kafka-2 kafka-3

ps: ## Показать статус сервисов
	$(COMPOSE) ps

clean: ## Удалить все контейнеры, volumes и сети
	$(COMPOSE) down -v --remove-orphans
	docker system prune -f

# =============================================================================
# Разработка
# =============================================================================

shell-backend: ## Открыть shell в backend контейнере
	$(COMPOSE) exec $(BACKEND_CONTAINER) /bin/bash

test: ## Запустить тесты
	$(COMPOSE) exec $(BACKEND_CONTAINER) pytest -v --cov=app --cov-report=html

test-unit: ## Запустить unit тесты
	$(COMPOSE) exec $(BACKEND_CONTAINER) pytest tests/unit -v

test-integration: ## Запустить integration тесты
	$(COMPOSE) exec $(BACKEND_CONTAINER) pytest tests/integration -v

lint: ## Проверить код линтером
	$(COMPOSE) exec $(BACKEND_CONTAINER) ruff check app tests

format: ## Отформатировать код
	$(COMPOSE) exec $(BACKEND_CONTAINER) ruff format app tests

# =============================================================================
# Миграции и данные
# =============================================================================

migrate: ## Применить миграции БД
	@echo "Миграции применяются автоматически при старте контейнеров"

generate-csv: ## Сгенерировать CSV с тестовыми данными (200k+ записей)
	python generator/csv_generator.py

start-generator: ## Запустить генератор событий для Kafka
	$(COMPOSE) --profile generator up -d generator

stop-generator: ## Остановить генератор событий
	$(COMPOSE) --profile generator stop generator

# =============================================================================
# Отказоустойчивость (демонстрация)
# =============================================================================

test-fault-tolerance: ## Запустить тест отказоустойчивости (PowerShell)
	@echo "Запуск тестов отказоустойчивости..."
	powershell -ExecutionPolicy Bypass -File tests/test_fault_tolerance.ps1

test-fault-tolerance-quick: ## Быстрый тест отказоустойчивости (PowerShell)
	@echo "Запуск быстрых тестов отказоустойчивости..."
	powershell -ExecutionPolicy Bypass -File tests/test_fault_tolerance.ps1

demo-fault-tolerance: ## Интерактивная демонстрация отказоустойчивости
	powershell -ExecutionPolicy Bypass -File tests/test_fault_tolerance.ps1

stop-kafka-2: ## Остановить Kafka брокер 2 (демо отказоустойчивости)
	$(COMPOSE) stop kafka-2
	@echo "Kafka-2 остановлен. Система продолжает работать."

start-kafka-2: ## Запустить Kafka брокер 2
	$(COMPOSE) start kafka-2

stop-clickhouse-2: ## Остановить ClickHouse реплику 2 (демо отказоустойчивости)
	$(COMPOSE) stop clickhouse-2
	@echo "ClickHouse-2 остановлен. Система продолжает работать."

start-clickhouse-2: ## Запустить ClickHouse реплику 2
	$(COMPOSE) start clickhouse-2

# =============================================================================
# Утилиты
# =============================================================================

kafka-topics: ## Показать список Kafka топиков
	$(COMPOSE) exec kafka-1 kafka-topics --bootstrap-server localhost:9092 --list

kafka-create-topic: ## Создать Kafka топик clickstream-events
	$(COMPOSE) exec kafka-1 kafka-topics --bootstrap-server localhost:9092 --create --topic clickstream-events --partitions 3 --replication-factor 2

clickhouse-client: ## Открыть ClickHouse клиент
	$(COMPOSE) exec clickhouse-1 clickhouse-client -u clickstream --password clickstream123

postgres-client: ## Открыть PostgreSQL клиент
	$(COMPOSE) exec postgres psql -U clickstream -d clickstream

# =============================================================================
# URLs сервисов
# =============================================================================

urls: ## Показать URLs всех сервисов
	@echo ""
	@echo "=== Clickstream Analytics Services ==="
	@echo ""
	@echo "Backend API:      http://localhost:8000"
	@echo "API Docs:         http://localhost:8000/docs"
	@echo "JS Tracker:       http://localhost:3000"
	@echo ""
	@echo "Kafka UI:         http://localhost:8080"
	@echo "Airflow:          http://localhost:8081 (admin/admin)"
	@echo "Grafana:          http://localhost:3001 (admin/admin)"
	@echo "Prometheus:       http://localhost:9090"
	@echo "Superset:         http://localhost:8088 (admin/admin)"
	@echo ""
	@echo "ClickHouse:       http://localhost:8123"
	@echo "PostgreSQL:       localhost:5432"
	@echo ""
