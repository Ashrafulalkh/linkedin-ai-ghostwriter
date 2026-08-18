#!/bin/bash

# Navigate to the project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "======================================================="
echo "⚡ Starting Daily LinkedIn AI Ghostwriter..."
echo "======================================================="

# Check if port 8501 is already running, if so, free it first
lsof -ti:8501 | xargs kill -9 2>/dev/null || true

# Start Streamlit server in the background
nohup python3 -m streamlit run app.py --server.port 8501 --server.headless true > server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > .server.pid

echo "Server started with PID: $SERVER_PID"
echo "Waiting for app to initialize..."

# Wait 2 seconds for server to boot
sleep 2

# Open in Google Chrome if installed, otherwise fallback to default browser
if [ -d "/Applications/Google Chrome.app" ]; then
    open -a "Google Chrome" "http://localhost:8501"
else
    open "http://localhost:8501"
fi

# Send macOS notification
osascript -e 'display notification "Daily LinkedIn AI Ghostwriter is now running at http://localhost:8501" with title "Ghostwriter Started" sound name "Glass"' 2>/dev/null || true

echo "======================================================="
echo "✔ Application is live at: http://localhost:8501"
echo "To stop the server anytime, simply double-click 'Stop_App.command'"
echo "======================================================="
sleep 2
