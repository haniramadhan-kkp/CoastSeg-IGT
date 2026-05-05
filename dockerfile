FROM ghcr.io/prefix-dev/pixi:latest

# Set working directory
WORKDIR /app

# Copy manifest and lock files
COPY pyproject.toml pixi.lock ./

# IMPORTANT: Copy LICENSE and README early because hatchling needs them to build the package
COPY LICENSE README.md ./

# Install default dependencies (Lightweight, no TensorFlow)
RUN pixi install --frozen

# Copy the rest of the application
COPY . .

# Environment variables
ENV PYTHONPATH=/app/src:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port for Jupyter Lab
EXPOSE 8888

# Default command to run Jupyter Lab using the default environment
CMD ["pixi", "run", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
