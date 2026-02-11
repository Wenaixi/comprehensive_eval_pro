FROM python:3.12-slim

# 安装系统依赖 (ddddocr 依赖 libgl1 和 libglib2.0-0)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 将项目代码拷贝到容器的子目录，并保持 package 结构
COPY . /app/comprehensive_eval_pro

CMD ["python", "-m", "comprehensive_eval_pro.main"]
