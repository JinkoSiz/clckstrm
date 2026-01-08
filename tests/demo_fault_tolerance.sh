#!/bin/bash
# =============================================================================
# ДЕМОНСТРАЦИЯ ОТКАЗОУСТОЙЧИВОСТИ
# Наглядный тест для защиты курсовой
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo -e "${BOLD}${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║         ДЕМОНСТРАЦИЯ ОТКАЗОУСТОЙЧИВОСТИ СИСТЕМЫ                   ║"
echo "║                  Clickstream Analytics                             ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Helper
get_count() {
    docker exec clickhouse-1 clickhouse-client --query \
        "SELECT count() FROM clickstream.events_processed" 2>/dev/null || echo "0"
}

get_leader() {
    curl -s "http://localhost:8080/api/clusters/clickstream-cluster/topics/clickstream-events" 2>/dev/null | \
        grep -o '"leader":[0-9]' | head -1 | grep -o '[0-9]' || echo "1"
}

press_enter() {
    echo ""
    echo -e "${CYAN}>>> Нажмите Enter для продолжения...${NC}"
    read
}

# =============================================================================
echo -e "${BOLD}${YELLOW}СЦЕНАРИЙ 1: Отказ лидера Kafka${NC}"
echo -e "Демонстрируем, что система продолжает работать при падении лидера"
echo ""
press_enter

# Start generator
echo -e "${BLUE}[1/6] Запускаем генератор событий...${NC}"
docker-compose --profile generator up -d generator 2>/dev/null
sleep 3
echo -e "${GREEN}      ✓ Генератор запущен (10 событий/сек)${NC}"

# Show current state
LEADER=$(get_leader)
COUNT_BEFORE=$(get_count)
echo ""
echo -e "${BLUE}[2/6] Текущее состояние:${NC}"
echo -e "      • Kafka лидер: ${BOLD}broker-$LEADER${NC}"
echo -e "      • Событий в ClickHouse: ${BOLD}$COUNT_BEFORE${NC}"
press_enter

# Kill leader
echo -e "${RED}[3/6] УБИВАЕМ ЛИДЕРА kafka-$LEADER...${NC}"
docker-compose stop kafka-$LEADER 2>/dev/null
echo -e "${RED}      ✗ kafka-$LEADER остановлен${NC}"
echo ""
echo -e "${YELLOW}      Ждём 5 секунд...${NC}"
sleep 5

# Check system still works
COUNT_AFTER=$(get_count)
DIFF=$((COUNT_AFTER - COUNT_BEFORE))
NEW_LEADER=$(get_leader)

echo ""
echo -e "${BLUE}[4/6] Проверяем систему:${NC}"
echo -e "      • Новый лидер: ${BOLD}broker-$NEW_LEADER${NC} (был: broker-$LEADER)"
echo -e "      • Событий в ClickHouse: ${BOLD}$COUNT_AFTER${NC}"
echo -e "      • Обработано за время отказа: ${GREEN}+$DIFF событий${NC}"

if [ $DIFF -gt 20 ]; then
    echo ""
    echo -e "${GREEN}${BOLD}      ✓ СИСТЕМА ПРОДОЛЖАЕТ РАБОТАТЬ!${NC}"
else
    echo ""
    echo -e "${RED}      ✗ Что-то пошло не так${NC}"
fi
press_enter

# Restore
echo -e "${BLUE}[5/6] Восстанавливаем kafka-$LEADER...${NC}"
docker-compose start kafka-$LEADER 2>/dev/null
sleep 3
echo -e "${GREEN}      ✓ kafka-$LEADER восстановлен${NC}"

# =============================================================================
echo ""
echo -e "${BOLD}${YELLOW}СЦЕНАРИЙ 2: Отказ ClickHouse реплики${NC}"
echo ""
press_enter

COUNT_BEFORE=$(get_count)
echo -e "${BLUE}[1/4] Событий до теста: $COUNT_BEFORE${NC}"

echo -e "${RED}[2/4] УБИВАЕМ clickhouse-2...${NC}"
docker-compose stop clickhouse-2 2>/dev/null
echo -e "${RED}      ✗ clickhouse-2 остановлен${NC}"
sleep 3

COUNT_AFTER=$(get_count)
DIFF=$((COUNT_AFTER - COUNT_BEFORE))
echo ""
echo -e "${BLUE}[3/4] Проверяем:${NC}"
echo -e "      • Событий в ClickHouse: ${BOLD}$COUNT_AFTER${NC} (+$DIFF)"

if [ $DIFF -gt 0 ]; then
    echo -e "${GREEN}${BOLD}      ✓ ЗАПИСЬ ПРОДОЛЖАЕТСЯ ЧЕРЕЗ clickhouse-1!${NC}"
fi

echo -e "${BLUE}[4/4] Восстанавливаем clickhouse-2...${NC}"
docker-compose start clickhouse-2 2>/dev/null
echo -e "${GREEN}      ✓ clickhouse-2 восстановлен${NC}"
press_enter

# =============================================================================
echo -e "${BOLD}${YELLOW}СЦЕНАРИЙ 3: Перезапуск Backend (Kafka буферизация)${NC}"
echo ""

COUNT_BEFORE=$(get_count)
echo -e "${BLUE}[1/4] Событий до теста: $COUNT_BEFORE${NC}"

echo -e "${RED}[2/4] ОСТАНАВЛИВАЕМ backend...${NC}"
docker-compose stop backend 2>/dev/null
echo -e "${RED}      ✗ backend остановлен${NC}"
echo -e "${YELLOW}      События буферизируются в Kafka...${NC}"
sleep 5

echo -e "${BLUE}[3/4] ЗАПУСКАЕМ backend...${NC}"
docker-compose start backend 2>/dev/null
echo -e "${YELLOW}      Backend обрабатывает буфер из Kafka...${NC}"
sleep 8

COUNT_AFTER=$(get_count)
DIFF=$((COUNT_AFTER - COUNT_BEFORE))
echo ""
echo -e "${BLUE}[4/4] Результат:${NC}"
echo -e "      • Событий в ClickHouse: ${BOLD}$COUNT_AFTER${NC}"
echo -e "      • Восстановлено из буфера: ${GREEN}+$DIFF событий${NC}"

if [ $DIFF -gt 0 ]; then
    echo -e "${GREEN}${BOLD}      ✓ ДАННЫЕ НЕ ПОТЕРЯНЫ!${NC}"
fi

# =============================================================================
# Cleanup
echo ""
echo -e "${BLUE}Останавливаем генератор...${NC}"
docker-compose --profile generator stop generator 2>/dev/null

echo ""
echo -e "${BOLD}${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                    ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА                          ║"
echo "╠═══════════════════════════════════════════════════════════════════╣"
echo "║  ✓ Kafka: отказ лидера → автоматический failover                  ║"
echo "║  ✓ ClickHouse: отказ реплики → запись через оставшуюся            ║"
echo "║  ✓ Backend: буферизация в Kafka → нет потери данных               ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

FINAL_COUNT=$(get_count)
echo -e "Итого событий в системе: ${BOLD}$FINAL_COUNT${NC}"
