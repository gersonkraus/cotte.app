#!/usr/bin/env bash

set -e

PROJECT_DIR="/home/gk/Projeto-izi"
MEMORY_DIR="$PROJECT_DIR/memory"
LOG_FILE="$MEMORY_DIR/.session-log"
LAST_FILE="$MEMORY_DIR/.last-session"

mkdir -p "$MEMORY_DIR"

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'no-git')"

echo "[$TIMESTAMP] sessão encerrada | branch=$BRANCH" >> "$LOG_FILE"
echo "$TIMESTAMP" > "$LAST_FILE"