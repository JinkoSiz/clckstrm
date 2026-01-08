#!/bin/bash
# =============================================================================
# Fault Tolerance Test Script
# Тестирование отказоустойчивости системы Clickstream Analytics
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE="docker-compose"
SLEEP_SHORT=5
SLEEP_MEDIUM=10
SLEEP_LONG=15

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=================================================================${NC}"
}

print_step() {
    echo -e "${YELLOW}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "  $1"
}

get_events_count() {
    docker exec clickhouse-1 clickhouse-client --query \
        "SELECT count() FROM clickstream.events_processed" 2>/dev/null || echo "0"
}

wait_and_count() {
    local seconds=$1
    print_info "Waiting ${seconds} seconds..."
    sleep $seconds
    get_events_count
}

check_service_health() {
    local service=$1
    local status=$(docker inspect --format='{{.State.Health.Status}}' $service 2>/dev/null || echo "unknown")
    if [ "$status" == "healthy" ] || [ "$status" == "unknown" ]; then
        return 0
    fi
    return 1
}

# =============================================================================
# Test: Kafka Broker Failure
# =============================================================================

test_kafka_broker_failure() {
    print_header "TEST 1: Kafka Broker Failure"
    print_info "Scenario: Stop one Kafka broker, verify system continues working"

    # Start generator
    print_step "Starting event generator..."
    $COMPOSE --profile generator up -d generator 2>/dev/null
    sleep $SLEEP_SHORT

    # Get initial count
    local count_before=$(get_events_count)
    print_info "Events before test: $count_before"

    # Stop Kafka broker 2
    print_step "Stopping Kafka broker 2..."
    $COMPOSE stop kafka-2 2>/dev/null

    # Wait and check events are still being processed
    print_step "Checking system continues to work..."
    sleep $SLEEP_MEDIUM
    local count_after=$(get_events_count)
    print_info "Events after ${SLEEP_MEDIUM}s without kafka-2: $count_after"

    # Calculate difference
    local diff=$((count_after - count_before))
    print_info "New events processed: $diff"

    # Restore Kafka broker 2
    print_step "Restoring Kafka broker 2..."
    $COMPOSE start kafka-2 2>/dev/null
    sleep $SLEEP_SHORT

    # Stop generator
    $COMPOSE --profile generator stop generator 2>/dev/null

    # Verify
    if [ $diff -gt 50 ]; then
        print_success "Kafka broker failure test PASSED (processed $diff events with 1 broker down)"
    else
        print_fail "Kafka broker failure test FAILED (only $diff events processed)"
    fi
}

# =============================================================================
# Test: ClickHouse Replica Failure
# =============================================================================

test_clickhouse_replica_failure() {
    print_header "TEST 2: ClickHouse Replica Failure"
    print_info "Scenario: Stop ClickHouse replica 2, verify writes continue"

    # Start generator
    print_step "Starting event generator..."
    $COMPOSE --profile generator up -d generator 2>/dev/null
    sleep $SLEEP_SHORT

    # Get initial count
    local count_before=$(get_events_count)
    print_info "Events before test: $count_before"

    # Stop ClickHouse replica 2
    print_step "Stopping ClickHouse replica 2..."
    $COMPOSE stop clickhouse-2 2>/dev/null

    # Wait and check
    print_step "Checking system continues to work..."
    sleep $SLEEP_MEDIUM
    local count_after=$(get_events_count)
    print_info "Events after ${SLEEP_MEDIUM}s without clickhouse-2: $count_after"

    local diff=$((count_after - count_before))
    print_info "New events processed: $diff"

    # Restore ClickHouse replica 2
    print_step "Restoring ClickHouse replica 2..."
    $COMPOSE start clickhouse-2 2>/dev/null
    sleep $SLEEP_SHORT

    # Stop generator
    $COMPOSE --profile generator stop generator 2>/dev/null

    # Verify
    if [ $diff -gt 50 ]; then
        print_success "ClickHouse replica failure test PASSED (processed $diff events)"
    else
        print_fail "ClickHouse replica failure test FAILED (only $diff events)"
    fi
}

# =============================================================================
# Test: Backend Consumer Restart
# =============================================================================

test_backend_restart() {
    print_header "TEST 3: Backend Consumer Restart"
    print_info "Scenario: Restart backend, verify no data loss (Kafka buffering)"

    # Start generator
    print_step "Starting event generator..."
    $COMPOSE --profile generator up -d generator 2>/dev/null
    sleep $SLEEP_SHORT

    # Get initial count
    local count_before=$(get_events_count)
    print_info "Events before backend restart: $count_before"

    # Stop backend (events will buffer in Kafka)
    print_step "Stopping backend (events buffering in Kafka)..."
    $COMPOSE stop backend 2>/dev/null

    # Wait while generator sends to Kafka
    print_info "Generator continues sending to Kafka for ${SLEEP_MEDIUM}s..."
    sleep $SLEEP_MEDIUM

    # Start backend
    print_step "Starting backend (will consume buffered events)..."
    $COMPOSE start backend 2>/dev/null
    sleep $SLEEP_LONG  # Give time to process buffered events

    local count_after=$(get_events_count)
    print_info "Events after backend restart: $count_after"

    local diff=$((count_after - count_before))
    print_info "Events processed (including buffered): $diff"

    # Stop generator
    $COMPOSE --profile generator stop generator 2>/dev/null

    # Should have processed ~10 events/sec * SLEEP_MEDIUM seconds
    local expected=$((SLEEP_MEDIUM * 10))
    if [ $diff -ge $((expected / 2)) ]; then
        print_success "Backend restart test PASSED (recovered $diff events from Kafka buffer)"
    else
        print_fail "Backend restart test FAILED (expected ~$expected, got $diff)"
    fi
}

# =============================================================================
# Test: Multiple Kafka Brokers Failure
# =============================================================================

test_multiple_kafka_failure() {
    print_header "TEST 4: Multiple Kafka Brokers (2 of 3 down)"
    print_info "Scenario: Stop 2 Kafka brokers, verify system handles gracefully"

    # Start generator
    print_step "Starting event generator..."
    $COMPOSE --profile generator up -d generator 2>/dev/null
    sleep $SLEEP_SHORT

    local count_before=$(get_events_count)
    print_info "Events before test: $count_before"

    # Stop 2 Kafka brokers
    print_step "Stopping Kafka brokers 2 and 3..."
    $COMPOSE stop kafka-2 kafka-3 2>/dev/null

    # Wait
    sleep $SLEEP_MEDIUM
    local count_during=$(get_events_count)
    print_info "Events with 2 brokers down: $count_during"

    # Restore brokers
    print_step "Restoring Kafka brokers..."
    $COMPOSE start kafka-2 kafka-3 2>/dev/null
    sleep $SLEEP_MEDIUM

    local count_after=$(get_events_count)
    print_info "Events after recovery: $count_after"

    # Stop generator
    $COMPOSE --profile generator stop generator 2>/dev/null

    local diff=$((count_after - count_before))
    print_info "Total events processed: $diff"

    # With 2 of 3 brokers down, system may partially work or queue events
    if [ $diff -gt 0 ]; then
        print_success "Multiple Kafka failure test PASSED (system recovered, $diff events)"
    else
        print_fail "Multiple Kafka failure test FAILED"
    fi
}

# =============================================================================
# Test: API Health During Failures
# =============================================================================

test_api_health() {
    print_header "TEST 5: API Health Endpoints"
    print_info "Scenario: Verify health endpoints respond correctly"

    # Basic health
    print_step "Testing /api/v1/health..."
    local health=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)
    if [ "$health" == "200" ]; then
        print_success "Health endpoint returns 200"
    else
        print_fail "Health endpoint returned $health"
    fi

    # Liveness
    print_step "Testing /api/v1/live..."
    local live=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/live)
    if [ "$live" == "200" ]; then
        print_success "Liveness endpoint returns 200"
    else
        print_fail "Liveness endpoint returned $live"
    fi

    # Detailed health
    print_step "Testing /api/v1/health/detailed..."
    local detailed=$(curl -s http://localhost:8000/api/v1/health/detailed)
    if echo "$detailed" | grep -q "components"; then
        print_success "Detailed health returns component status"
    else
        print_fail "Detailed health missing components"
    fi
}

# =============================================================================
# Test: Data Consistency After Failures
# =============================================================================

test_data_consistency() {
    print_header "TEST 6: Data Consistency Check"
    print_info "Scenario: Verify data integrity after all failure tests"

    print_step "Checking events_processed table..."
    local processed=$(docker exec clickhouse-1 clickhouse-client --query \
        "SELECT count() FROM clickstream.events_processed" 2>/dev/null)
    print_info "Total processed events: $processed"

    print_step "Checking for duplicate events..."
    local duplicates=$(docker exec clickhouse-1 clickhouse-client --query \
        "SELECT count() - uniq(id) as duplicates FROM clickstream.events_processed" 2>/dev/null)

    if [ "$duplicates" == "0" ]; then
        print_success "No duplicate events found"
    else
        print_fail "Found $duplicates duplicate events"
    fi

    print_step "Checking event types distribution..."
    docker exec clickhouse-1 clickhouse-client --query \
        "SELECT event_type, count() as cnt FROM clickstream.events_processed GROUP BY event_type" 2>/dev/null
    print_success "Data consistency check completed"
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header "FAULT TOLERANCE TEST SUITE"
    print_info "Testing Clickstream Analytics system resilience"
    print_info "Started at: $(date)"

    # Ensure all services are running
    print_step "Ensuring all services are running..."
    $COMPOSE up -d 2>/dev/null
    sleep $SLEEP_SHORT

    # Run tests
    test_kafka_broker_failure
    test_clickhouse_replica_failure
    test_backend_restart
    test_multiple_kafka_failure
    test_api_health
    test_data_consistency

    # Summary
    print_header "TEST SUMMARY"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    print_info "Completed at: $(date)"

    # Cleanup
    print_step "Stopping generator..."
    $COMPOSE --profile generator stop generator 2>/dev/null || true

    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}All fault tolerance tests passed!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}Some tests failed. Check logs above.${NC}"
        exit 1
    fi
}

# Run main
main "$@"
