#!/bin/bash
# =============================================================================
# Quick Fault Tolerance Test
# Быстрый тест отказоустойчивости (2-3 минуты)
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE="docker-compose"
PASSED=0
FAILED=0

echo -e "${BLUE}=== QUICK FAULT TOLERANCE TEST ===${NC}"
echo ""

# Helper functions
get_count() {
    docker exec clickhouse-1 clickhouse-client --query \
        "SELECT count() FROM clickstream.events_processed" 2>/dev/null || echo "0"
}

get_kafka_leader() {
    # Get leader broker ID for clickstream-events topic partition 0
    # Returns broker ID (1, 2, or 3)
    local leader=$(curl -s "http://localhost:8080/api/clusters/clickstream-cluster/topics/clickstream-events" 2>/dev/null | \
        grep -o '"leader":[0-9]' | head -1 | grep -o '[0-9]' || echo "1")
    echo "$leader"
}

# =============================================================================
# TEST 1: Kafka Leader Broker Failure
# =============================================================================
echo -e "${YELLOW}TEST 1: Kafka Leader Broker Failure${NC}"

# Start generator
$COMPOSE --profile generator up -d generator 2>/dev/null
sleep 3

# Find current leader
LEADER=$(get_kafka_leader)
echo "  Current Kafka leader for partition 0: broker $LEADER"

count1=$(get_count)
echo "  Events before: $count1"

# Stop the LEADER broker
echo "  Stopping kafka-$LEADER (the leader)..."
$COMPOSE stop kafka-$LEADER 2>/dev/null
sleep 5

count2=$(get_count)
diff=$((count2 - count1))
echo "  Events after leader (kafka-$LEADER) down: $count2 (+$diff)"

# Check new leader
NEW_LEADER=$(get_kafka_leader)
echo "  New leader elected: broker $NEW_LEADER"

# Restore
echo "  Restoring kafka-$LEADER..."
$COMPOSE start kafka-$LEADER 2>/dev/null
sleep 2

if [ $diff -gt 20 ]; then
    echo -e "${GREEN}  ✓ PASSED (leader failover worked, new leader: $NEW_LEADER)${NC}"
    ((PASSED++))
else
    echo -e "${RED}  ✗ FAILED${NC}"
    ((FAILED++))
fi

# =============================================================================
# TEST 2: ClickHouse Replica Failure
# =============================================================================
echo ""
echo -e "${YELLOW}TEST 2: ClickHouse Replica Failure${NC}"

count1=$(get_count)
echo "  Events before: $count1"

# Stop clickhouse-2
$COMPOSE stop clickhouse-2 2>/dev/null
sleep 5

count2=$(get_count)
diff=$((count2 - count1))
echo "  Events after clickhouse-2 down: $count2 (+$diff)"

# Restore
$COMPOSE start clickhouse-2 2>/dev/null

if [ $diff -gt 20 ]; then
    echo -e "${GREEN}  ✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}  ✗ FAILED${NC}"
    ((FAILED++))
fi

# =============================================================================
# TEST 3: Backend Restart (Kafka Buffering)
# =============================================================================
echo ""
echo -e "${YELLOW}TEST 3: Backend Restart (Kafka Buffering)${NC}"

count1=$(get_count)
echo "  Events before: $count1"

# Stop backend
$COMPOSE stop backend 2>/dev/null
echo "  Backend stopped, events buffering in Kafka..."
sleep 5

# Start backend
$COMPOSE start backend 2>/dev/null
echo "  Backend started, processing buffered events..."
sleep 8

count2=$(get_count)
diff=$((count2 - count1))
echo "  Events after restart: $count2 (+$diff)"

if [ $diff -gt 0 ]; then
    echo -e "${GREEN}  ✓ PASSED (recovered $diff buffered events from Kafka)${NC}"
    ((PASSED++))
else
    echo -e "${RED}  ✗ FAILED (no events recovered)${NC}"
    ((FAILED++))
fi

# =============================================================================
# TEST 4: API Health
# =============================================================================
echo ""
echo -e "${YELLOW}TEST 4: API Health Check${NC}"

sleep 2
health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null)
if [ "$health" == "200" ]; then
    echo -e "${GREEN}  ✓ API healthy (HTTP $health)${NC}"
    ((PASSED++))
else
    echo -e "${RED}  ✗ API unhealthy (HTTP $health)${NC}"
    ((FAILED++))
fi

# =============================================================================
# Cleanup
# =============================================================================
echo ""
echo -e "${YELLOW}Cleanup...${NC}"
$COMPOSE --profile generator stop generator 2>/dev/null

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BLUE}=== SUMMARY ===${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

total_events=$(get_count)
echo ""
echo "Total events in system: $total_events"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}All fault tolerance tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
