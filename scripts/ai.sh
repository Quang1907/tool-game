#!/usr/bin/env bash
# AI Master Engineer Automation CLI Wrapper
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_EXEC="${REPO_ROOT}/.venv/bin/python3"

if [ ! -f "${PYTHON_EXEC}" ]; then
    PYTHON_EXEC="python3"
fi

if [ "$#" -eq 0 ]; then
    echo "Sử dụng: ./scripts/ai.sh [status | audit | resume | validate-docs]"
    exit 1
fi

CMD="$1"
case "$CMD" in
    status|ai:status)
        "${PYTHON_EXEC}" "${SCRIPT_DIR}/ai_tools.py" status
        ;;
    audit|ai:audit)
        "${PYTHON_EXEC}" "${SCRIPT_DIR}/ai_tools.py" audit
        ;;
    resume|ai:resume)
        "${PYTHON_EXEC}" "${SCRIPT_DIR}/ai_tools.py" resume
        ;;
    validate-docs|ai:validate-docs)
        "${PYTHON_EXEC}" "${SCRIPT_DIR}/ai_tools.py" validate-docs
        ;;
    *)
        echo "Lệnh không hợp lệ: $CMD"
        echo "Các lệnh hỗ trợ: status, audit, resume, validate-docs"
        exit 1
        ;;
esac
