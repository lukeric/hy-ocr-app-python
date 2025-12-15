#!/bin/bash
#
# Keep Azure Container Apps Alive Script
# Purpose: Calls the health API regularly to prevent ACA from scaling down to zero
# Duration: 3 hours by default, then automatically stops
# Usage: ./keep_alive.sh [interval_seconds] [duration_hours]
#   Example: ./keep_alive.sh 30 3      # 30 seconds interval, 3 hours duration
#   Example: ./keep_alive.sh 60 2      # 60 seconds interval, 2 hours duration
#   Example: ./keep_alive.sh           # Use defaults (30 seconds, 3 hours)
#

# Default configuration
HEALTH_URL="https://hunyuan-ocr.ashybay-2b080a17.japaneast.azurecontainerapps.io/health"
DEFAULT_INTERVAL_SECONDS=30  # Call every 30 seconds by default
DEFAULT_DURATION_HOURS=3

# Parse command-line arguments
INTERVAL_SECONDS=${1:-$DEFAULT_INTERVAL_SECONDS}
DURATION_HOURS=${2:-$DEFAULT_DURATION_HOURS}
DURATION_SECONDS=$((DURATION_HOURS * 3600))

# Validate arguments
if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || [ "$INTERVAL_SECONDS" -le 0 ]; then
    echo "Error: Interval must be a positive integer (seconds)"
    echo "Usage: $0 [interval_seconds] [duration_hours]"
    exit 1
fi

if ! [[ "$DURATION_HOURS" =~ ^[0-9]+$ ]] || [ "$DURATION_HOURS" -le 0 ]; then
    echo "Error: Duration must be a positive integer (hours)"
    echo "Usage: $0 [interval_seconds] [duration_hours]"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Start time
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_SECONDS))

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Azure Container Apps Keep-Alive Script${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Health endpoint: ${YELLOW}${HEALTH_URL}${NC}"
if [ $INTERVAL_SECONDS -ge 60 ]; then
    echo -e "Check interval: ${YELLOW}${INTERVAL_SECONDS}${NC} seconds ($(($INTERVAL_SECONDS / 60)) minutes)"
else
    echo -e "Check interval: ${YELLOW}${INTERVAL_SECONDS}${NC} seconds"
fi
echo -e "Total duration: ${YELLOW}${DURATION_HOURS}${NC} hours"
echo -e "Start time: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "End time: ${YELLOW}$(date -r ${END_TIME} '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Counter for requests
REQUEST_COUNT=0

# Function to call health endpoint
call_health_api() {
    local current_time=$(date '+%Y-%m-%d %H:%M:%S')
    REQUEST_COUNT=$((REQUEST_COUNT + 1))
    
    echo -n "[${current_time}] Request #${REQUEST_COUNT}: Calling health API... "
    
    # Call the API with timeout
    response=$(curl -s -w "\n%{http_code}" --connect-timeout 10 --max-time 30 "${HEALTH_URL}" 2>&1)
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        # Extract HTTP status code (last line)
        http_code=$(echo "$response" | tail -n 1)
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "200" ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP ${http_code})"
            if [ ! -z "$body" ]; then
                echo "    Response: $body"
            fi
        else
            echo -e "${RED}✗ FAILED${NC} (HTTP ${http_code})"
            if [ ! -z "$body" ]; then
                echo "    Response: $body"
            fi
        fi
    else
        echo -e "${RED}✗ ERROR${NC} (curl exit code: ${exit_code})"
    fi
}

# Function to calculate remaining time
get_remaining_time() {
    local current=$(date +%s)
    local remaining=$((END_TIME - current))
    
    if [ $remaining -le 0 ]; then
        echo "0h 0m 0s"
        return
    fi
    
    local hours=$((remaining / 3600))
    local minutes=$(((remaining % 3600) / 60))
    local seconds=$((remaining % 60))
    
    echo "${hours}h ${minutes}m ${seconds}s"
}

# Main loop
echo -e "${YELLOW}Starting keep-alive loop...${NC}"
echo ""

while true; do
    current_time=$(date +%s)
    
    # Check if we've exceeded the duration
    if [ $current_time -ge $END_TIME ]; then
        echo ""
        echo -e "${BLUE}================================================${NC}"
        echo -e "${GREEN}✓ Duration limit reached (${DURATION_HOURS} hours)${NC}"
        echo -e "Total requests made: ${YELLOW}${REQUEST_COUNT}${NC}"
        echo -e "End time: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
        echo -e "${BLUE}================================================${NC}"
        echo -e "${YELLOW}Script stopped. ACA will scale down to zero after idle timeout.${NC}"
        exit 0
    fi
    
    # Call the health API
    call_health_api
    
    # Show remaining time
    remaining=$(get_remaining_time)
    echo -e "    Time remaining: ${BLUE}${remaining}${NC}"
    echo ""
    
    # Calculate sleep time (don't sleep past the end time)
    time_until_end=$((END_TIME - $(date +%s)))
    if [ $time_until_end -lt $INTERVAL_SECONDS ]; then
        sleep_time=$time_until_end
        echo -e "${YELLOW}Sleeping for ${sleep_time} seconds (final wait)...${NC}"
    else
        sleep_time=$INTERVAL_SECONDS
        if [ $sleep_time -ge 60 ]; then
            echo -e "Sleeping for ${sleep_time} seconds ($(($sleep_time / 60)) minutes)..."
        else
            echo -e "Sleeping for ${sleep_time} seconds..."
        fi
    fi
    
    sleep $sleep_time
    echo ""
done

