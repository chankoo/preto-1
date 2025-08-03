#!/bin/bash

# Start Jupyter Notebook without authentication
jupyter notebook --notebook-dir=/app/notebooks --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' &

# Start Streamlit app
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
