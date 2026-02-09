# Docker 运行（交互式 CLI）

Docker 主要解决：

- 统一 Python 环境与依赖安装
- 在不同机器上快速运行同一套逻辑（仍需你确保合法合规与授权）

## 方式 A：docker run（推荐）

构建镜像：

```bash
docker build -t comprehensive-eval-pro:latest .
```

准备一个宿主机目录用于持久化（token/缓存/验证码）：

```bash
mkdir -p runtime
```

运行（交互式，支持输入学号/密码/验证码）：

```bash
docker run --rm -it ^
  -e SILICONFLOW_API_KEY= ^
  -e CEP_CONFIG_FILE=/data/config.json ^
  -e CEP_CACHE_FILE=/data/content_cache.json ^
  -e CEP_CAPTCHA_FILE=/data/captcha.jpg ^
  -v "%cd%\\runtime:/data" ^
  comprehensive-eval-pro:latest
```

说明：

- 不需要 AI 就不要设置 `SILICONFLOW_API_KEY`，程序会回退到缓存/默认文案。
- 容器里不会自动弹出验证码图片；请按提示到 `runtime/captcha.jpg` 打开查看。
- 如需在容器里使用本地资源图片，可额外挂载：

```bash
docker run --rm -it ^
  -e CEP_CONFIG_FILE=/data/config.json ^
  -v "%cd%\\runtime:/data" ^
  -v "%cd%\\assets\\images:/app/comprehensive_eval_pro/assets/images" ^
  comprehensive-eval-pro:latest
```

## 方式 B：docker compose

```bash
docker compose up --build
```

## Docker 构建失败：无法拉取 python 基础镜像

如果你看到类似错误（无法从 Docker Hub 获取 token/超时）：

- `failed to fetch anonymous token ... auth.docker.io ... timeout`

通常是网络/代理问题：

- 确认 Docker Desktop 已配置代理或可直连外网
- 先手动执行 `docker pull python:3.12-slim` 验证能否拉取基础镜像
- 受限网络环境下配置 registry mirror（镜像加速）

