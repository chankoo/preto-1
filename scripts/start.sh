#!/bin/bash

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Set the PYTHONPATH to include the src directory
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/src"

# Sync markdown files before starting services
echo "🔄 Syncing markdown files..."
if [ -f "${SCRIPT_DIR}/sync-markdown.sh" ]; then
    cd "${PROJECT_ROOT}" && ./scripts/sync-markdown.sh
else
    echo "⚠️  Markdown sync script not found, skipping..."
fi

# Start Jupyter Notebook using the config file
cd "${PROJECT_ROOT}"
jupyter notebook --config=jupyter_notebook_config.py &

# Start Streamlit app
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

