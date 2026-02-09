# Comprehensive Eval Pro（综合评价自动化系统）

[![License](https://img.shields.io/github/license/Wenaixi/comprehensive_eval_pro?style=flat)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat)](docs/quickstart.md)

## 重要声明（请先阅读）

本项目仅用于学习研究与安全合规的工程实践（例如：在你拥有所有权或获得明确授权的系统中进行接口调试、自动化测试、逆向分析方法论复现）。

严禁用于任何未授权的访问、绕过认证、批量提交、数据抓取或其它可能侵害第三方权益的行为。使用者需自行确保：

- 仅在**合法合规**且**获得授权**的环境中运行。
- 仅使用你本人账号与数据，避免对真实业务造成影响。
- 充分理解自动化请求可能触发风控、封禁或法律风险。

如果你不确定是否有授权，请不要运行。

## 文档导航

- [docs/README.md](docs/README.md)：文档入口（目录）
- [docs/quickstart.md](docs/quickstart.md)：快速开始（安装/测试/运行）
- [docs/accounts-and-tokens.md](docs/accounts-and-tokens.md)：批量账号、Token 持久化与无人值守
- [docs/resources.md](docs/resources.md)：本地资源目录（图片/班会 Excel）规则
- [docs/docker.md](docs/docker.md)：Docker 运行
- [docs/troubleshooting.md](docs/troubleshooting.md)：排障与合规建议

## 怎么运行（本地）

在你获得授权的环境中，从 `comprehensive_eval_pro` 的上一级目录运行：

```bash
python -m comprehensive_eval_pro
```

运行时会：

- 先读取 `accounts.txt`（或 `CEP_ACCOUNTS_FILE` 指定路径），对所有账号执行预登录并把 token/user_info 写入 `config.json`
- 再展示账号列表并支持多选（全选/反选/追加/移除），后续操作只应用到所选账号集合
- 再进入“任务二级菜单”：先选任务集合（y/bh/gq/ld/jx/序号），再选处理范围（完成未完成/重做已完成/全部重做）
- 文案多样性按“任务名”独立计次：默认每 3 次提交强制生成 1 次新文案（可用 `CEP_DIVERSITY_EVERY` 调整）
- 每个账号会输出 1 份简洁日志（默认：`runtime/summary_logs/`，可用 `CEP_SUMMARY_LOG_DIR` 覆盖）

## 常用文件

- `.env.example`：环境变量（每个变量前有详细解释；复制为 `.env` 使用）
- `config.example.json`：配置模板（复制为 `config.json`）
- `accounts.example.txt`：批量账号文件模板（复制为 `accounts.txt`）

## 贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 安全问题反馈

请阅读 [SECURITY.md](SECURITY.md)。

## 免责声明

见 [DISCLAIMER.md](DISCLAIMER.md)。

## 许可证

本项目以 MIT License 发布，见 [LICENSE](LICENSE)。

## 作者与联系

- Wenaixi
- cep@wenxi.dev

## 支持

如果这个项目对你有帮助，欢迎点个 Star。
