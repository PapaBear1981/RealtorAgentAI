#!/bin/bash

# Start Celery Workers Script for RealtorAgentAI Platform
# This script starts multiple Celery workers for different task queues

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

# Function to start a worker
start_worker() {
    local worker_name=$1
    local queues=$2
    local concurrency=${3:-4}
    local log_level=${4:-info}
    
    echo "Starting worker: $worker_name (queues: $queues, concurrency: $concurrency)"
    
    celery -A app.core.celery_app worker \
        --hostname="$worker_name@%h" \
        --queues="$queues" \
        --concurrency="$concurrency" \
        --loglevel="$log_level" \
        --logfile="$LOG_DIR/$worker_name.log" \
        --pidfile="$PID_DIR/$worker_name.pid" \
        --time-limit=3600 \
        --soft-time-limit=1800 \
        --max-tasks-per-child=1000 \
        --without-gossip \
        --without-mingle \
        --without-heartbeat \
        --detach
    
    echo "Worker $worker_name started successfully"
}

# Function to check if worker is running
is_worker_running() {
    local worker_name=$1
    local pid_file="$PID_DIR/$worker_name.pid"
    
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

# Function to stop a worker
stop_worker() {
    local worker_name=$1
    local pid_file="$PID_DIR/$worker_name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "Stopping worker: $worker_name (PID: $pid)"
        
        if ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 30 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                echo "Force killing worker: $worker_name"
                kill -KILL "$pid"
            fi
        fi
        
        rm -f "$pid_file"
        echo "Worker $worker_name stopped"
    else
        echo "Worker $worker_name is not running"
    fi
}

# Function to show worker status
show_status() {
    echo "=== Celery Worker Status ==="
    
    local workers=("ingest_worker" "ocr_worker" "llm_worker" "export_worker" "system_worker")
    
    for worker in "${workers[@]}"; do
        if is_worker_running "$worker"; then
            local pid=$(cat "$PID_DIR/$worker.pid")
            echo "✓ $worker: Running (PID: $pid)"
        else
            echo "✗ $worker: Stopped"
        fi
    done
    
    echo ""
    echo "=== Queue Status ==="
    celery -A app.core.celery_app inspect active_queues 2>/dev/null || echo "No active workers found"
}

# Main script logic
case "${1:-start}" in
    start)
        echo "Starting Celery workers for RealtorAgentAI Platform..."
        
        # Start specialized workers for different queues
        start_worker "ingest_worker" "ingest" 4 "info"
        start_worker "ocr_worker" "ocr" 2 "info"
        start_worker "llm_worker" "llm" 2 "info"
        start_worker "export_worker" "export" 3 "info"
        start_worker "system_worker" "system" 1 "info"
        
        echo ""
        echo "All workers started successfully!"
        echo "Log files: $LOG_DIR/"
        echo "PID files: $PID_DIR/"
        echo ""
        show_status
        ;;
        
    stop)
        echo "Stopping Celery workers..."
        
        stop_worker "ingest_worker"
        stop_worker "ocr_worker"
        stop_worker "llm_worker"
        stop_worker "export_worker"
        stop_worker "system_worker"
        
        echo "All workers stopped"
        ;;
        
    restart)
        echo "Restarting Celery workers..."
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        show_status
        ;;
        
    logs)
        local worker_name=${2:-"ingest_worker"}
        local log_file="$LOG_DIR/$worker_name.log"
        
        if [ -f "$log_file" ]; then
            echo "Showing logs for $worker_name:"
            tail -f "$log_file"
        else
            echo "Log file not found: $log_file"
            echo "Available log files:"
            ls -la "$LOG_DIR"/*.log 2>/dev/null || echo "No log files found"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [worker_name]}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all Celery workers"
        echo "  stop     - Stop all Celery workers"
        echo "  restart  - Restart all Celery workers"
        echo "  status   - Show worker status"
        echo "  logs     - Show logs for a worker (default: ingest_worker)"
        echo ""
        echo "Available workers:"
        echo "  - ingest_worker  (file processing)"
        echo "  - ocr_worker     (text extraction)"
        echo "  - llm_worker     (AI processing)"
        echo "  - export_worker  (document generation)"
        echo "  - system_worker  (maintenance tasks)"
        exit 1
        ;;
esac
