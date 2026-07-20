# ═══════════════════════════════════════════════════════
# 后端构建 — Python 3.11 + PyTorch CPU 版本
# 使用 CPU 版本 PyTorch 减小镜像体积（约 500MB vs 2GB+）
# ═══════════════════════════════════════════════════════

FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 安装系统依赖（OpenCV 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖清单，利用 Docker 缓存层
COPY requirements.txt .

# 安装 PyTorch CPU 版本（必须指定 --index-url）
RUN pip install --upgrade pip && \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# 拷贝应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/uploads /app/detections /app/logs

EXPOSE 8000

# 使用 uvicorn 启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
