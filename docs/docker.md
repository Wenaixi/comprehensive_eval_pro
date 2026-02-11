# 🐳 Docker 部署指南

CEP 提供官方 Docker 支持，旨在解决跨环境运行的依赖与配置一致性问题。

---

## 🚀 1. 快速构建与运行

### 构建镜像
```bash
docker build -t cep:latest .
```

### 推荐启动命令 (交互式)
```bash
docker run --rm -it \
  -v "$(pwd)/configs:/app/comprehensive_eval_pro/configs" \
  -v "$(pwd)/runtime:/app/comprehensive_eval_pro/runtime" \
  -v "$(pwd)/assets:/app/comprehensive_eval_pro/assets" \
  cep:latest
```

---

## 📂 2. 卷挂载说明 (Volumes)

| 容器路径 | 宿主机路径 (建议) | 作用 |
| :--- | :--- | :--- |
| `/app/comprehensive_eval_pro/configs` | `./configs` | 持久化 Token 和配置文件 |
| `/app/comprehensive_eval_pro/runtime` | `./runtime` | 查看运行日志和调试信息 |
| `/app/comprehensive_eval_pro/assets` | `./assets` | 提供本地图片和文档素材 |

---

## 🛠️ 3. Docker Compose (多任务编排)

使用项目根目录下的 `docker-compose.yml` 快速启动：

```yaml
version: '3.8'
services:
  cep:
    build: .
    volumes:
      - ./configs:/app/comprehensive_eval_pro/configs
      - ./runtime:/app/comprehensive_eval_pro/runtime
    environment:
      - SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY}
    stdin_open: true
    tty: true
```

运行命令：
```bash
docker-compose up --build
```

---

## ❓ 常见问题

### 网络受限导致构建失败
如果在拉取 `python:3.12-slim` 时遇到超时，请尝试配置 Docker 镜像加速器或检查代理设置。

### 交互模式问题
在 Windows CMD 下运行 Docker 时，如果无法输入验证码，请确保使用了 `-it` 参数并尝试在 PowerShell 中运行。
