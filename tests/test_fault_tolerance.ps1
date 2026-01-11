# Test Fault Tolerance - PowerShell version
# Quick test (~2 min)

Write-Host "=== Kafka Fault Tolerance Test ===" -ForegroundColor Cyan
Write-Host ""

# Check containers are running
Write-Host "[1/5] Checking containers..." -ForegroundColor Yellow
$kafkaStatus = docker-compose ps kafka-1 kafka-2 kafka-3 --format json 2>$null | ConvertFrom-Json
$runningKafka = ($kafkaStatus | Where-Object { $_.State -eq "running" }).Count
if ($runningKafka -lt 3) {
    Write-Host "ERROR: Not all Kafka brokers are running ($runningKafka/3)" -ForegroundColor Red
    exit 1
}
Write-Host "OK: All 3 Kafka brokers running" -ForegroundColor Green

# Check initial event count
Write-Host ""
Write-Host "[2/5] Getting initial event count..." -ForegroundColor Yellow
$initialCount = docker-compose exec -T clickhouse-1 clickhouse-client --query "SELECT count() FROM clickstream.events_raw" 2>$null
Write-Host "Initial events: $initialCount" -ForegroundColor Green

# Get leader broker from Kafka UI
Write-Host ""
Write-Host "[3/5] Finding Kafka leader broker..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/clusters/clickstream-cluster/topics/clickstream-events" -ErrorAction Stop
    $leader = $response.partitions[0].leader
    $leaderContainer = "kafka-$leader"
    Write-Host "Leader broker: $leaderContainer (broker id: $leader)" -ForegroundColor Green
} catch {
    Write-Host "Could not determine leader, using kafka-1" -ForegroundColor Yellow
    $leaderContainer = "kafka-1"
}

# Kill the leader
Write-Host ""
Write-Host "[4/5] Killing leader: $leaderContainer" -ForegroundColor Yellow
docker-compose stop $leaderContainer 2>$null
Write-Host "Leader stopped. Waiting 30 seconds for failover..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check events still coming
Write-Host ""
Write-Host "[5/5] Checking events after failover..." -ForegroundColor Yellow
$afterCount = docker-compose exec -T clickhouse-1 clickhouse-client --query "SELECT count() FROM clickstream.events_raw" 2>$null
$newEvents = [int]$afterCount - [int]$initialCount
Write-Host "Events after failover: $afterCount (new: $newEvents)" -ForegroundColor Green

# Restart killed broker
Write-Host ""
Write-Host "Restarting $leaderContainer..." -ForegroundColor Yellow
docker-compose start $leaderContainer 2>$null

# Results
Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan
if ($newEvents -gt 0) {
    Write-Host "SUCCESS: System continued processing $newEvents events during failover" -ForegroundColor Green
    exit 0
} else {
    Write-Host "WARNING: No new events detected (may need to check generator)" -ForegroundColor Yellow
    exit 1
}
