# 🚀 Comprehensive Eval Pro (CEP)
### 究极专业级·综合评价自动化破解系统

[![License](https://img.shields.io/github/license/Wenaixi/comprehensive_eval_pro?style=for-the-badge&color=blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green?style=for-the-badge&logo=python)](docs/quickstart.md)
[![Status](https://img.shields.io/badge/Status-Ultra_Stable-orange?style=for-the-badge)](CLAUDE.md)

CEP 是一个为“高效、稳定、全能”而生的自动化框架。它不仅是一个工具，更是一套完整的、模块化的工程解决方案，旨在通过 AI 视觉与逻辑编排，彻底破解繁杂的综合评价流程。

---

## 🌟 核心特性 (Core Features)

- **🧠 视觉大一统 (Vision 3.0)**: 集成 AI 多模型轮询与本地 OCR 兜底，支持 1MB 强制智能压缩与验证码智能保护。
- **📁 路径智能感知 (Path Intelligence)**: 真正的“环境无关”运行，无论从何处启动，系统都能精准定位资源。
- **🛡️ 究极稳健性**: 110+ 单元测试覆盖，Fail-Safe 容错机制确保批量任务绝不因个别错误而中断。
- **📝 文案多样性**: 基于任务独立计次的 AI 内容生成，配合“任务二级菜单”，实现精细化任务管控。
- **📊 原子化审计**: 自动生成详细的运行报告 (`runtime/summary_logs/`)，每一步操作均可回溯。

---

## 📖 文档导航 (Documentation)

| 模块 | 说明 | 链接 |
| :--- | :--- | :--- |
| **快速上手** | 环境搭建、测试运行、基础操作 | [🚀 Quickstart](docs/quickstart.md) |
| **账户管理** | 批量账号配置、Token 持久化、无人值守 | [🔑 Accounts](docs/accounts-and-tokens.md) |
| **资源规则** | 图片素材、班会 Excel、目录结构规范 | [📂 Resources](docs/resources.md) |
| **容器部署** | Docker 一键部署、镜像构建说明 | [🐳 Docker](docs/docker.md) |
| **故障排查** | 常见问题解决、合规运行建议 | [🛠️ Troubleshooting](docs/troubleshooting.md) |

---

## ⚡ 快速运行 (Quick Start)

在确保已获得合法授权的前提下，从项目根目录运行：

```powershell
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python -m comprehensive_eval_pro
```

### 运行逻辑概览：
1. **预登录**: 自动解析 `accounts.txt` 并刷新 Token 至 `configs/state.json`。
2. **账号筛选**: 交互式菜单支持全选、反选、多选账号。
3. **任务编排**: 
   - 任务集：班会(bh)、军训(jx)、劳动(ld)、国旗(gq)等。
   - 范围：仅未完成、重做已完成、全部重做。
4. **多样性保障**: 每 3 次提交自动触发 AI 重写文案（可配置）。

---

## 🛠️ 配置说明 (Configuration)

- `configs.example/`: 提供 `settings.example.yaml` 模板。
- `configs/`: 存放实际配置（**敏感信息，Git 已忽略**）。
- `accounts.txt`: 存放账号密码（**Git 已忽略**，请参考 `accounts.example.txt`）。

---

## ⚖️ 法律与合规声明

**严正声明**：本项目仅用于学习研究与安全合规的工程实践。严禁用于任何未授权的访问、批量提交或其它侵害第三方权益的行为。使用者需自行承担因不当使用产生的法律风险。

---

## 🤝 贡献与反馈

- **贡献**: 请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
- **安全**: 发现漏洞？请查阅 [SECURITY.md](SECURITY.md)。
- **作者**: Wenaixi ([cep@wenxi.dev](mailto:cep@wenxi.dev))

---

> 如果这个项目对你有帮助，欢迎点个 **Star** ⭐，这是对开发者最大的鼓励。
