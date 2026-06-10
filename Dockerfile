FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    langgraph \
    langchain-community \
    langchain-openai \
    langchain-google-genai \
    langchain-ollama \
    pydantic \
    pypdf

# Copy application files
COPY . .

# Expose port
EXPOSE 8001

# Run the app. app.py runs database initialization on start if mock_erp.db is missing.
CMD ["python", "app.py"]
