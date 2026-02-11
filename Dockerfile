# 使用轻量级 Python 3.12 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量：
# 1. 禁止 Python 生成 .pyc 文件
# 2. 禁止缓冲标准输出，确保日志实时可见
# 3. 设置 PYTHONPATH 确保包导入正常
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装系统级依赖
# ddddocr 需要 libgl1 和 libglib2.0-0 才能运行
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 预安装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目核心代码
# 采用相对路径拷贝，确保包结构完整
COPY . /app/comprehensive_eval_pro

# 创建必要的运行时目录，并赋予权限
RUN mkdir -p /app/comprehensive_eval_pro/runtime \
             /app/comprehensive_eval_pro/configs \
             /app/comprehensive_eval_pro/assets

# 默认启动命令：运行主程序模块
# 交互式运行建议配合 -it 参数
CMD ["python", "-m", "comprehensive_eval_pro"]
