# Clickstream Analytics

Система real-time аналитики кликстрима с отказоустойчивой архитектурой.

## Стек технологий

- **Backend**: Python, FastAPI
- **Streaming**: Apache Kafka (3 брокера)
- **Storage**: ClickHouse (2 реплики)
- **ETL**: Apache Airflow
- **Monitoring**: Prometheus, Grafana
- **Analytics**: Apache Superset

## Просмотр диаграмм и схем

### UML-диаграммы (PlantUML)

Файлы в `docs/diagrams/`:
- `architecture.puml` - архитектура системы
- `sequence.puml` - последовательность обработки события
- `usecase.puml` - use case диаграмма
- `activity.puml` - блок-схема обработки

**Способы просмотра:**

- **PlantUML Online:** https://www.plantuml.com/plantuml/uml
   - Скопировать содержимое файла → вставить → Generate

### Схема БД (DBML)

Файл: `docs/dbml/schema.dbml`

**Способы просмотра:**

- **dbdiagram.io:** https://dbdiagram.io/d
   - Скопировать содержимое файла → вставить

## Запуск

```bash
docker-compose up -d # Необходимо подождать около 2-5 минут для полной инициализации
```

## Тестирование

## 1. Тестирование API через Postman

### Импорт коллекции
1. Откройте Postman
2. **File → Import → Upload Files**
3. Выберите файл `api/postman_collection.json`
4. Переменная `base_url` уже настроена на `http://localhost:8000`

```bash
curl localhost:8000/api/v1/health  # {"status":"ok"}
```

Postman-коллекция: `api/postman_collection.json`

### Kafka (потоковая обработка) 
```bash
make start-generator # Генератор будет записывать по 10 событий в секунду постоянно
```

### ETL (Airflow)
```bash
docker exec airflow-webserver airflow dags trigger clickstream_etl # Или через UI
```

UI: http://localhost:8081 (admin/admin)

### Отказоустойчивость
```bash
make test-fault-tolerance
```

### Unit-тесты
```bash
make test

docker-compose exec backend pytest -v --cov=app --cov-report=term-missing # 45 passed, coverage ~65%
```

## Web-интерфейсы

| Сервис | URL | Логин |
|--------|-----|-------|
| Swagger | http://localhost:8000/docs | - |
| Grafana | http://localhost:3001 | admin/admin |
| Superset | http://localhost:8088 | admin/admin |
| Kafka UI | http://localhost:8080 | - |
| Airflow | http://localhost:8081 | admin/admin |

## Документация

- UML-диаграммы: `docs/diagrams/`
- DBML-схема: `docs/dbml/schema.dbml`
