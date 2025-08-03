#!/bin/bash

# Start Flower Monitoring Dashboard Script for RealtorAgentAI Platform
# This script starts the Flower web-based monitoring tool for Celery

set -e

# Configuration
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="${BACKEND_DIR}/.venv"
LOG_DIR="${BACKEND_DIR}/logs"
PID_DIR="${BACKEND_DIR}/pids"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Activate virtual environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "Activated virtual environment: $VENV_PATH"
else
    echo "Warning: Virtual environment not found at $VENV_PATH"
fi

# Change to backend directory
cd "$BACKEND_DIR"

# Configuration from environment variables or defaults
FLOWER_PORT=${FLOWER_PORT:-5555}
FLOWER_ADDRESS=${FLOWER_ADDRESS:-0.0.0.0}
FLOWER_BASIC_AUTH=${FLOWER_BASIC_AUTH:-""}
FLOWER_URL_PREFIX=${FLOWER_URL_PREFIX:-""}
FLOWER_DB=${FLOWER_DB:-"$BACKEND_DIR/flower.db"}

# Function to start Flower
start_flower() {
    echo "Starting Flower monitoring dashboard..."
    
    local flower_args=(
        "--broker=redis://localhost:6379/1"
        "--port=$FLOWER_PORT"
        "--address=$FLOWER_ADDRESS"
        "--db=$FLOWER_DB"
        "--logging=info"
        "--enable_events"
        "--natural_time"
        "--tasks_columns=name,uuid,state,args,kwargs,result,received,started,runtime,worker"
        "--purge_offline_workers=300"
        "--auto_refresh"
    )
    
    # Add basic auth if configured
    if [ -n "$FLOWER_BASIC_AUTH" ]; then
        flower_args+=("--basic_auth=$FLOWER_BASIC_AUTH")
    fi
    
    # Add URL prefix if configured
    if [ -n "$FLOWER_URL_PREFIX" ]; then
        flower_args+=("--url_prefix=$FLOWER_URL_PREFIX")
    fi
    
    # Start Flower in background
    celery -A app.core.celery_app flower \
        "${flower_args[@]}" \
        --logfile="$LOG_DIR/flower.log" \
        --pidfile="$PID_DIR/flower.pid" \
        &
    
    local flower_pid=$!
    echo $flower_pid > "$PID_DIR/flower.pid"
    
    echo "Flower started successfully!"
    echo "PID: $flower_pid"
    echo "URL: http://$FLOWER_ADDRESS:$FLOWER_PORT$FLOWER_URL_PREFIX"
    echo "Log file: $LOG_DIR/flower.log"
    echo "Database: $FLOWER_DB"
    
    # Wait a moment and check if it's still running
    sleep 2
    if ps -p $flower_pid > /dev/null 2>&1; then
        echo "Flower is running successfully"
    else
        echo "Error: Flower failed to start. Check the log file for details."
        exit 1
    fi
}

# Function to check if Flower is running
is_flower_running() {
    local pid_file="$PID_DIR/flower.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to stop Flower
stop_flower() {
    local pid_file="$PID_DIR/flower.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "Stopping Flower (PID: $pid)..."
        
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "Force killing Flower"
                kill -KILL "$pid"
            fi
        fi
        
        rm -f "$pid_file"
        echo "Flower stopped"
    else
        echo "Flower is not running"
    fi
}

# Function to show Flower status
show_status() {
    echo "=== Flower Monitoring Dashboard Status ==="
    
    if is_flower_running; then
        local pid=$(cat "$PID_DIR/flower.pid")
        echo "✓ Flower: Running (PID: $pid)"
        echo "  URL: http://$FLOWER_ADDRESS:$FLOWER_PORT$FLOWER_URL_PREFIX"
        echo "  Log: $LOG_DIR/flower.log"
        echo "  Database: $FLOWER_DB"
        
        # Check if port is accessible
        if command -v curl >/dev/null 2>&1; then
            if curl -s "http://localhost:$FLOWER_PORT$FLOWER_URL_PREFIX" >/dev/null; then
                echo "  Status: Accessible"
            else
                echo "  Status: Not accessible (may still be starting)"
            fi
        fi
    else
        echo "✗ Flower: Stopped"
    fi
}

# Function to show logs
show_logs() {
    local log_file="$LOG_DIR/flower.log"
    
    if [ -f "$log_file" ]; then
        echo "Showing Flower logs:"
        tail -f "$log_file"
    else
        echo "Log file not found: $log_file"
    fi
}

# Main script logic
case "${1:-start}" in
    start)
        if is_flower_running; then
            echo "Flower is already running"
            show_status
        else
            start_flower
        fi
        ;;
        
    stop)
        stop_flower
        ;;
        
    restart)
        echo "Restarting Flower..."
        stop_flower
        sleep 2
        start_flower
        ;;
        
    status)
        show_status
        ;;
        
    logs)
        show_logs
        ;;
        
    config)
        echo "=== Flower Configuration ==="
        echo "Port: $FLOWER_PORT"
        echo "Address: $FLOWER_ADDRESS"
        echo "URL Prefix: ${FLOWER_URL_PREFIX:-'(none)'}"
        echo "Database: $FLOWER_DB"
        echo "Basic Auth: ${FLOWER_BASIC_AUTH:+'configured'}"
        echo "Log Directory: $LOG_DIR"
        echo "PID Directory: $PID_DIR"
        echo ""
        echo "Environment Variables:"
        echo "  FLOWER_PORT=$FLOWER_PORT"
        echo "  FLOWER_ADDRESS=$FLOWER_ADDRESS"
        echo "  FLOWER_URL_PREFIX=$FLOWER_URL_PREFIX"
        echo "  FLOWER_BASIC_AUTH=${FLOWER_BASIC_AUTH:+'***'}"
        echo "  FLOWER_DB=$FLOWER_DB"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|config}"
        echo ""
        echo "Commands:"
        echo "  start    - Start Flower monitoring dashboard"
        echo "  stop     - Stop Flower monitoring dashboard"
        echo "  restart  - Restart Flower monitoring dashboard"
        echo "  status   - Show Flower status"
        echo "  logs     - Show Flower logs"
        echo "  config   - Show Flower configuration"
        echo ""
        echo "Environment Variables:"
        echo "  FLOWER_PORT        - Port to run Flower on (default: 5555)"
        echo "  FLOWER_ADDRESS     - Address to bind to (default: 0.0.0.0)"
        echo "  FLOWER_BASIC_AUTH  - Basic auth credentials (format: user:password)"
        echo "  FLOWER_URL_PREFIX  - URL prefix for reverse proxy setup"
        echo "  FLOWER_DB          - Database file path"
        echo ""
        echo "Example:"
        echo "  FLOWER_PORT=8080 FLOWER_BASIC_AUTH=admin:secret $0 start"
        exit 1
        ;;
esac
