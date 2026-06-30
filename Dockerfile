FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the unified requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend source code and workspace
COPY services/ ./services/
COPY workspace/ ./workspace/

# Copy the start script and make it executable
COPY start.sh .
RUN chmod +x start.sh

# Expose the internal ports locally (useful for debugging, though Render maps $PORT)
EXPOSE 8000 8001 8002

# Run the unified start script
CMD ["./start.sh"]
