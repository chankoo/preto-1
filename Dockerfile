# Base image from python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ps -ef 명령어 사용을 위한 의존성 설치
RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy the rest of the application
COPY . .

# Copy Jupyter configuration
COPY jupyter_notebook_config.py /root/.jupyter/

# Expose streamlit and jupyter ports
EXPOSE 8501 8888

# Make start script executable
RUN chmod +x start.sh

# Command to run the app
CMD ["./start.sh"]