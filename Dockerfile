# HarmonyLab Dockerfile
# Python 3.12 with MS SQL ODBC driver for Cloud Run

FROM python:3.12-slim-bookworm

# Install system dependencies and ODBC driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Install poppler for PDF-to-image conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    (pip uninstall -y onnxruntime-gpu || true) && \
    pip install --no-cache-dir onnxruntime

# Pre-download oemer model checkpoints at build time (avoids 10-min download on first request)
# Files: unet_big/{model.onnx, weights.h5}, seg_net/{model.onnx, weights.h5}
RUN OEMER_DIR=$(python -c "import oemer; import os; print(os.path.dirname(oemer.__file__))") && \
    mkdir -p "$OEMER_DIR/checkpoints/unet_big" "$OEMER_DIR/checkpoints/seg_net" && \
    curl -fSL -o "$OEMER_DIR/checkpoints/unet_big/model.onnx" \
      "https://github.com/BreezeWhite/oemer/releases/download/checkpoints/1st_model.onnx" && \
    curl -fSL -o "$OEMER_DIR/checkpoints/unet_big/weights.h5" \
      "https://github.com/BreezeWhite/oemer/releases/download/checkpoints/1st_weights.h5" && \
    curl -fSL -o "$OEMER_DIR/checkpoints/seg_net/model.onnx" \
      "https://github.com/BreezeWhite/oemer/releases/download/checkpoints/2nd_model.onnx" && \
    curl -fSL -o "$OEMER_DIR/checkpoints/seg_net/weights.h5" \
      "https://github.com/BreezeWhite/oemer/releases/download/checkpoints/2nd_weights.h5" && \
    echo "oemer checkpoints downloaded to $OEMER_DIR/checkpoints"

# Copy application code
COPY . .

# Cloud Run uses PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
