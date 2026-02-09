# 快速开始（仅本地学习/测试）

## 1) Python 环境

- 推荐：Python 3.12+
- Windows / PowerShell

安装依赖：

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

依赖提示：

- Python 3.12 环境下建议使用 `ddddocr==1.5.6`，避免兼容性问题。
- 班会 Excel 解析依赖 `pandas` + `xlrd`（已包含在 requirements.txt）。

## 2) 环境变量（可选）

- 复制 `.env.example` 为 `.env`
- 按需填写

说明：`.env.example` 里每个变量前都有逐项解释。

## 3) 配置文件

建议以模板为基础创建你的本地配置：

- 复制 `config.example.json` 为 `config.json`
- 按需填写 `model`、`username`、`password` 等

提醒：账号、密码、token、用户信息等属于敏感数据，`config.json` 默认被 `.gitignore` 忽略。

## 4) 运行单元测试（推荐）

在仓库根目录执行：

```bash
python -m unittest -q
```

如果你安装了 `pytest`：

```bash
pytest -q
```

## 5) 交互式入口（谨慎）

仅在你获得授权的环境中做联调时运行：

```bash
cd ..
python -m comprehensive_eval_pro
```

当前入口默认按“多账号批量”模式运行：会读取 `accounts.txt`（或 `CEP_ACCOUNTS_FILE` 指定路径），逐个账号执行任务流程。
多账号流程会先对所有账号执行预登录并把 token/user_info 写入 `config.json`，再进入账号选择（全选/反选/追加/移除）。
任务选择改为二级菜单：先选任务集合（y/bh/gq/ld/jx/序号），再选处理范围（只处理未完成/重做已完成/全部重做）。
文案多样性计次按“任务名”独立统计：默认每 3 次提交强制生成 1 次新文案（其余走缓存），可用 `CEP_DIVERSITY_EVERY` 调整。
每个账号会生成 1 份简洁日志（默认输出到 `runtime/summary_logs/`，可用 `CEP_SUMMARY_LOG_DIR` 覆盖）。
