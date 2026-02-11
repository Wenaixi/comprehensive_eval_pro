# 📚 CEP 文档中心

欢迎来到 Comprehensive Eval Pro (CEP) 的官方文档中心。这里包含了从零开始搭建环境到深层架构解析的所有资料。

## 🔍 文档概览

### 1. 🚀 [快速上手 (Quickstart)](quickstart.md)
- 环境依赖 (Python 3.10+)
- 配置文件初始化
- 基础运行流程与测试验证

### 2. 🔑 [账户与会话 (Accounts & Tokens)](accounts-and-tokens.md)
- 批量账号格式规范
- Token 持久化机制 (`state.json`)
- 无人值守模式配置

### 3. 📂 [资源与规则 (Resources & Rules)](resources.md)
- `assets/` 目录结构详解
- 图片上传自动处理机制
- 班会记录文件解析优先级

### 4. 🐳 [容器化部署 (Docker)](docker.md)
- Docker 镜像构建
- 卷挂载 (Volumes) 与持久化
- Compose 一键启动

### 5. 🛠️ [故障排查 (Troubleshooting)](troubleshooting.md)
- 常见错误代码处理
- 验证码识别优化建议
- 依赖冲突解决方法

---

## 🏗️ 核心架构简述

CEP 采用 **模块化** 架构设计：
- `services/`: 核心业务逻辑（视觉、内容生成、权限验证等）。
- `utils/`: 通用工具集（HTTP 客户端、文档解析器等）。
- `configs/`: 动静分离的配置管理。
- `runtime/`: 运行时产生的日志与临时文件。

> **提示**：建议先阅读 [快速上手](quickstart.md) 开始你的第一步。
