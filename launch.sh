#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Westway Tennis Monitor — launcher
#  Runs the monitor in the background, logs to monitor.log
#  Usage: ./launch.sh          (start)
#         ./launch.sh stop     (stop)
#         ./launch.sh status   (check if running)
# ─────────────────────────────────────────────────────────────

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$DIR/.monitor.pid"
VENV="$DIR/.venv/bin/activate"
LOG="$DIR/monitor.log"

start() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Monitor is already running (PID $(cat "$PIDFILE"))."
        exit 0
    fi

    echo "Starting Westway Tennis Monitor..."
    source "$VENV"
    nohup python "$DIR/main.py" --schedule >> "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started (PID $!). Logs: $LOG"
}

stop() {
    if [ ! -f "$PIDFILE" ]; then
        echo "Monitor is not running (no PID file found)."
        exit 0
    fi
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PIDFILE"
        echo "Monitor stopped (PID $PID)."
    else
        echo "Process $PID not found — removing stale PID file."
        rm -f "$PIDFILE"
    fi
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "Monitor is running (PID $(cat "$PIDFILE"))."
        echo "Last 5 log lines:"
        tail -5 "$LOG"
    else
        echo "Monitor is not running."
    fi
}

case "${1:-start}" in
    start)  start  ;;
    stop)   stop   ;;
    status) status ;;
    *)      echo "Usage: $0 {start|stop|status}" ; exit 1 ;;
esac
