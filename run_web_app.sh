#!/bin/bash
#
# Run HunyuanOCR Web App
# Usage: ./run_web_app.sh [port]
#   Example: ./run_web_app.sh 5001
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Default port (5001 to avoid conflict with macOS AirPlay on 5000)
PORT="${1:-5001}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  HunyuanOCR Web App${NC}"
echo -e "${BLUE}================================================${NC}"

# Stop any previous instance running on the same port
echo -e "${YELLOW}Checking for existing processes on port ${PORT}...${NC}"
EXISTING_PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo -e "${RED}Stopping existing process (PID: $EXISTING_PID) on port ${PORT}...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 1
    echo -e "${GREEN}✓ Previous instance stopped${NC}"
else
    echo -e "${GREEN}✓ Port ${PORT} is available${NC}"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/update dependencies if requirements.txt is newer than installed packages
if [ "requirements.txt" -nt "venv/.installed" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt --quiet
    touch venv/.installed
fi

echo -e "${GREEN}Starting web app on port ${PORT}...${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Open in browser: ${GREEN}http://127.0.0.1:${PORT}${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Run the app
PORT=$PORT python ocr_web_app.py

