# Docker 部署指南

本系统支持通过 Docker 进行容器化部署，确保环境一致性。

## 1. 快速启动

在项目根目录下执行部署脚本：
```powershell
./deploy.ps1
```

或者手动执行 Compose 命令：
```bash
docker-compose up -d --build
```

## 2. 卷挂载 (Volumes) 说明

为实现数据持久化，以下目录需挂载至宿主机：

- `/app/configs`: 存放 `settings.yaml` 配置文件。
- `/app/assets`: 存放任务素材。
- `/app/logs`: 存放审计日志。
- `/app/storage`: 存放运行状态与 Token。
- `/app/data`: 存放账户列表。

## 3. 容器管理

### 查看日志
```bash
docker logs -f cep-app
```

### 进入交互式终端
```bash
docker exec -it cep-app /bin/bash
```

## 4. 注意事项

- **时区配置**: 容器默认使用 UTC 时区，若需同步本地时间，请在 `docker-compose.yml` 中配置 `TZ` 环境变量。
- **资源限制**: 建议为容器分配至少 1GB 内存，以应对大文件 OCR 解析。
