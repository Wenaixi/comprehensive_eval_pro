# 快速开始 (Quickstart)

本指南将帮助您快速搭建 CEP 环境并启动自动化任务。

## 1. 环境准备

- **Python**: 3.10+ (推荐 3.12)
- **依赖安装**:
  ```powershell
  pip install -r requirements.txt
  ```

## 2. 核心配置

1. **凭证配置**: 在 `configs/settings.yaml` 中配置 API Key 与登录凭证。
2. **账户导入**: 将待处理账户填入 `data/accounts.txt`，格式为 `账号 密码`。
3. **资源放置**: 按照分类（如 `主题班会`）将素材放入 `assets/` 对应层级。

## 3. 启动流程

### 本地启动
```powershell
python -m comprehensive_eval_pro
```

### 验证启动 (推荐)
首次运行建议先执行测试套件：
```powershell
pytest tests/
```

## 4. 关键目录说明

- `/assets`: 存放任务素材（按分类、学校、年级、班级分层）。
- `/configs`: 存放静态配置 `settings.yaml` 与动态状态 `state.json`。
- `/data`: 存放账户列表 `accounts.txt`。
- `/logs`: 存放运行审计日志。

## 5. 任务过滤与范围 (Mode & Scope)

系统支持通过配置文件或命令行参数精细控制执行范围：

- **Scope (执行范围)**:
  - `pending`: 仅处理未完成的任务（默认）。
  - `done`: 仅处理已完成的任务。
  - `all`: 全量处理。
- **Selection (任务选择)**:
  - `bh`: 仅处理主题班会。
  - `ld`: 仅处理劳动任务。
  - `jx`: 仅处理军训任务。
  - `gq`: 仅处理国旗下讲话。
  - `indices`: 处理指定索引的任务。

## 6. 常见操作

- **清理缓存**: 删除 `configs/state.json` 即可重置运行状态。
- **强制同步**: 修改 `default_task_mode` 为 `all` 可强制重新提交任务。
