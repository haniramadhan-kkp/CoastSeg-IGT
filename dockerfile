FROM ghcr.io/prefix-dev/pixi:latest

# Set working directory
WORKDIR /app

# Copy lock and manifest files
COPY pyproject.toml pixi.lock ./

# Install dependencies including ML features for CoastSat classifier
# We use --frozen to ensure exact versions from pixi.lock
RUN pixi install --frozen -e ml

# Copy the rest of the application
COPY . .

# Ensure the app is installed in editable mode within the environment
RUN pixi run -e ml pip install -e .

# Environment variables
ENV PYTHONPATH=/app/src:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port for Jupyter Lab
EXPOSE 8888

# Default command to run Jupyter Lab
# Using 0.0.0.0 to allow access from outside the container
CMD ["pixi", "run", "-e", "ml", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
