# Preto Project Makefile

.PHONY: sync-markdown install run clean help start

# Default target
help:
	@echo "Available commands:"
	@echo "  sync-markdown  - Sync markdown files from notebooks/proposals to src/services/proposals"
	@echo "  install        - Install Python dependencies"
	@echo "  start          - Start all services (Jupyter + Streamlit)"
	@echo "  run            - Run Streamlit app only"
	@echo "  clean          - Remove symbolic links and temp files"
	@echo "  help           - Show this help message"

# Sync markdown files using symbolic links
sync-markdown:
	@./scripts/sync-markdown.sh

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Start all services (recommended)
start:
	@echo "🚀 Starting all services..."
	./scripts/start.sh

# Run Streamlit app only
run:
	@echo "🚀 Starting Streamlit app only..."
	streamlit run src/app.py

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	find src/services/proposals -name "*.md" -type l -delete 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed"