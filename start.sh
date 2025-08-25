#!/bin/bash

# Set the PYTHONPATH to include the src directory
export PYTHONPATH="${PYTHONPATH}:/app/src"

# Sync markdown files before starting services
echo "🔄 Syncing markdown files..."
if [ -f "/app/scripts/sync-markdown.sh" ]; then
    cd /app && ./scripts/sync-markdown.sh
else
    echo "⚠️  Markdown sync script not found, skipping..."
fi

# Start Jupyter Notebook using the config file
jupyter notebook --config=/app/jupyter_notebook_config.py &

# Start Streamlit app
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

