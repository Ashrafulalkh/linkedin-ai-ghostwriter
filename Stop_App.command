#!/bin/bash

# Navigate to the project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "======================================================="
echo "🛑 Stopping Daily LinkedIn AI Ghostwriter..."
echo "======================================================="

# Kill process by saved PID if exists
if [ -f .server.pid ]; then
    PID=$(cat .server.pid)
    kill -9 $PID 2>/dev/null || true
    rm -f .server.pid
fi

# Kill any process running on port 8501 or matching app.py
lsof -ti:8501 | xargs kill -9 2>/dev/null || true
pkill -f "streamlit run app.py" 2>/dev/null || true

# Send macOS notification
osascript -e 'display notification "Daily LinkedIn AI Ghostwriter server has been stopped." with title "Ghostwriter Stopped" sound name "Pop"' 2>/dev/null || true

echo "✔ Server stopped successfully."
echo "======================================================="
sleep 2
