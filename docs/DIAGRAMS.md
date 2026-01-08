# Диаграммы и схемы

## UML-диаграммы

### Архитектура системы
![Architecture](https://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/your-repo/main/docs/diagrams/architecture.puml)

**Локальный просмотр:** откройте `docs/diagrams/architecture.puml` в:
- https://www.plantuml.com/plantuml/uml (скопировать содержимое)
- VSCode с расширением PlantUML (Alt+D)

```
docs/diagrams/
├── architecture.puml  - Компоненты системы и их связи
├── sequence.puml      - Последовательность обработки события
├── usecase.puml       - Варианты использования
└── activity.puml      - Блок-схема обработки запроса
```

### Описание диаграмм

#### architecture.puml
Показывает все компоненты системы:
- **Data Sources**: JS Tracker, HTTP API, CSV, Kafka Producer
- **Backend**: FastAPI, Event Processor, Kafka Consumer
- **Message Broker**: Kafka Cluster (3 брокера) + ZooKeeper
- **Storage**: PostgreSQL (OLTP), ClickHouse Cluster (OLAP)
- **ETL**: Apache Airflow с DAG
- **Monitoring**: Prometheus, Grafana, Superset

#### sequence.puml
Три сценария:
1. Event Collection via HTTP (JS Tracker → API → ClickHouse)
2. Event Collection via Kafka (Generator → Kafka → Consumer → ClickHouse)
3. ETL Processing (Airflow DAG)

#### usecase.puml
Акторы и их действия:
- **Web User**: генерирует события (views, clicks)
- **Analyst**: смотрит статистику и отчёты
- **Admin**: управляет системой и мониторингом
- **Developer**: интегрирует трекер и API

#### activity.puml
Пошаговый процесс обработки HTTP запроса:
1. Reception → Validation → Processing → Storage → Response

---

## Схема базы данных (DBML)

Файл: `docs/dbml/schema.dbml`

**Просмотр:** https://dbdiagram.io/d (скопировать содержимое)

### Таблицы PostgreSQL (OLTP)
| Таблица | Назначение |
|---------|------------|
| users | Справочник пользователей |
| pages | Справочник страниц |
| sessions | Данные сессий |

### Таблицы ClickHouse (OLAP)
| Таблица | Назначение |
|---------|------------|
| events_raw | Сырые события |
| events_processed | Обогащённые события |
| daily_stats | Дневная статистика |
| hourly_stats | Часовая статистика |
| page_stats | Статистика по страницам |
| device_stats | Статистика по устройствам |
| element_stats | Статистика по элементам (для heatmap) |
| user_activity | DAU/WAU/MAU метрики |
| session_stats | Статистика сессий |

---

## Быстрый просмотр (онлайн)

1. **PlantUML:** https://www.plantuml.com/plantuml/uml
2. **DBML:** https://dbdiagram.io/d

Скопируйте содержимое файла и вставьте в редактор.
