# 🚀 快速开始

本指南将带你快速搭建 CEP 运行环境。请确保你已获得相关系统的合法授权。

## 🛠️ 1. 环境准备

- **Python**: 3.10+ (推荐 3.12)
- **操作系统**: Windows (推荐 PowerShell) / Linux / macOS

### 安装步骤

```powershell
# 克隆/下载项目后进入根目录
cd comprehensive_eval_pro

# 创建并激活虚拟环境 (可选但推荐)
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate # Linux/macOS

# 安装依赖
pip install -r requirements.txt
```

> **💡 提示**：Python 3.12 用户如遇 `ddddocr` 安装问题，请指定版本 `pip install ddddocr==1.5.6`。

---

## ⚙️ 2. 配置初始化

CEP 采用“动静分离”的配置体系，确保你的凭据安全。

1. **自动初始化**: 首次运行 `python -m comprehensive_eval_pro` 时，系统会自动从 `configs.example/` 复制模板。
2. **手动配置**:
   - `configs/settings.yaml`: 修改 `siliconflow_api_key` 以启用 AI 能力。
   - `accounts.txt`: 参考 `accounts.example.txt` 填入学号与密码。

---

## 🏃 3. 启动程序

得益于 **路径智能感知 (Path Intelligence)**，你现在可以在任何位置启动项目，而无需担心路径错误。

### 推荐启动方式
从项目根目录运行：
```powershell
python -m comprehensive_eval_pro
```

### 运行流程详解
1. **预登录阶段**: 自动检测所有账号状态，有效 Token 直接复用，失效则自动触发 OCR 登录。
2. **账号选择**: 交互式勾选目标账号。
3. **任务下发**: 选择任务类型（班会/军训等）及范围（未完成/全部）。
4. **自动化执行**: 自动匹配资源、AI 生成内容并提交，结果实时记录在 `runtime/summary_logs/`。

---

## 🧪 4. 验证与测试

在正式运行前，强烈建议执行自动化测试以确保一切正常：

```powershell
# 运行所有单元测试
pytest -v
```

---

## 📂 5. 核心目录速览

- `assets/`: 存放你的图片和文档资源。
- `configs/`: 你的私人配置中心。
- `runtime/`: 系统运行时的输出（日志、缓存、临时图片）。
