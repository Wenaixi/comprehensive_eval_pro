# Comprehensive Eval Pro（综合评价自动化系统）

## 重要声明（请先阅读）

本项目仅用于学习研究与安全合规的工程实践（例如：在你拥有所有权或获得明确授权的系统中进行接口调试、自动化测试、逆向分析方法论复现）。

严禁用于任何未授权的访问、绕过认证、批量提交、数据抓取或其它可能侵害第三方权益的行为。使用者需自行确保：

- 仅在**合法合规**且**获得授权**的环境中运行。
- 仅使用你本人账号与数据，避免对真实业务造成影响。
- 充分理解自动化请求可能触发风控、封禁或法律风险。

如果你不确定是否有授权，请不要运行。

## 项目概览

`comprehensive_eval_pro` 是一个偏“工程化集成”的 Python 项目，目标是把一套复杂的登录/会话建立流程与任务处理流程模块化封装，并提供：

- 交互式入口（命令行）：登录、会话恢复、任务扫描、逐条预览并提交
- 认证模块：会话初始化、验证码获取/预校验、学校 ID 溯源、Token 捕获
- 内容生成模块：对接第三方大模型（可选）生成活动心得，并做本地缓存
- 任务管理模块：激活业务 Session、拉取任务、生成 Payload、预览审计、提交
- 完整单元测试：使用 mock/响应桩，避免对真实系统产生网络调用

## 目录结构

```
comprehensive_eval_pro/
  main.py                  # 交互式主入口
  config.json               # 本地运行配置（默认被 .gitignore 忽略）
  config.example.json       # 配置模板
  requirements.txt          # 依赖
  services/
    auth.py                 # SSO 认证（验证码、学校ID、Token）
    content_gen.py          # AI 文案生成与缓存
    file_service.py         # 文件/图片上传（如有）
    task_manager.py         # 任务扫描、payload 构造、预览/提交
  utils/
    excel_parser.py         # Excel 解析（班会等场景）
  assets/
    images/                 # 本地资源（图片/Excel等）
```

## 快速开始（仅本地学习/测试）

### 1) Python 环境

- 推荐：Python 3.12+
- Windows / PowerShell

创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

依赖说明：

- Python 3.12 环境下建议使用 `ddddocr==1.5.6`，避免兼容性问题。
- 班会 Excel 解析依赖 `pandas` + `xlrd`（已包含在 requirements.txt）。

### 2) 配置环境变量（可选）

项目可选使用第三方大模型 API 生成文案：

- 复制 `.env.example` 为 `.env`
- 填写 `SILICONFLOW_API_KEY`

注意：程序只读取本项目目录下的 `.env`；请勿把真实密钥提交到任何代码仓库。

### 3) 配置文件

建议以模板为基础创建你的本地配置：

- 复制 `config.example.json` 为 `config.json`
- 按需填写 `model`、`username`、`password` 等

默认模型：`deepseek-ai/DeepSeek-V3.2`

提醒：账号、密码、token、用户信息等属于敏感数据，不建议写入仓库；默认已在 `.gitignore` 忽略 `config.json`，程序也会在缺失时从 `config.example.json` 自动生成一份本地 `config.json`。

常用配置项（均在 `config.example.json` 中给出默认值）：

- `sso_base`：SSO 登录域名（默认 `https://www.nazhisoft.com`）
- `base_url`：业务系统地址（注意：如为 HTTP，将有明文传输风险）
- `upload_url`：图片上传地址
- `model`：文案生成模型名称（仅在配置了 `SILICONFLOW_API_KEY` 时生效）

运行时文件位置（可选覆盖）：

- 默认情况下：`config.json`、`content_cache.json`、`captcha.jpg` 都会写在本项目目录下。
- 如需自定义路径（适合 Docker/服务器）：可设置环境变量
  - `CEP_CONFIG_FILE`：配置文件路径
  - `CEP_CACHE_FILE`：文案缓存文件路径
  - `CEP_CAPTCHA_FILE`：验证码图片输出路径

### 4) 准备本地资源（可选）

项目支持从本地资源目录中自动随机选图并上传（用于“劳动/军训/国旗下讲话/主题班会”等场景）。请把资源放到以下四个目录之一：

```
assets/images/
  国旗下讲话/          # 直接放图片文件（不要再套子文件夹）
  军训/                # 直接放图片文件（不要再套子文件夹）
  劳动/                # 直接放图片文件（不要再套子文件夹）
  主题班会/
    <某次班会资源包目录>/  # 一个班会一个文件夹，里面放图片 + 可选 .xls
```

图片格式要求：

- 支持：`.jpg/.jpeg/.png/.webp/.bmp/.tif/.tiff`
- 上传前会自动转换为 JPG 再上传（临时文件，上传后自动清理，不会改动原图）

“国旗下讲话 / 军训 / 劳动”三类目录规则：

- 只会扫描目录下**第一层文件**（不会递归子目录）
- 文件名不限，放多张会随机抽取一张

“主题班会”目录规则（重点）：

- 目录结构：`assets/images/主题班会/<班会资源包目录>/`
- `<班会资源包目录>` 内至少放 1 张图片；可额外放 1 个班会记录 Excel（目前只识别 `.xls`）
- 程序会尝试“按日期优先匹配资源包目录”：从任务名提取 `M.D / MM.DD / YYYY.M.D` 形式日期，与资源包目录名里的日期做匹配
  - 建议资源包目录名以日期开头，例如：`2025.9.29高一（8）班《百年薪火传，青春报国时》`

Docker 提醒：

- 默认 Docker 构建会忽略 `assets/images/`（避免镜像过大）；如需在 Docker 中使用本地资源，请用 volume 挂载该目录到容器内的 `/app/comprehensive_eval_pro/assets/images/`，或调整 `.dockerignore`。

## 运行方式

本仓库更推荐通过单元测试来理解与验证逻辑（默认不会对真实系统发起请求）。

### 运行单元测试

在仓库根目录执行：

```bash
python -m unittest -q
```

如果你额外安装了 `pytest`，也可以使用：

```bash
pytest -q
```

### 交互式入口（谨慎）

如果你在**获得授权**的环境中做联调，可运行：

```bash
python -m comprehensive_eval_pro.main
```

程序支持：

- 自动 OCR（如果安装了 `ddddocr`）或手动输入验证码
- 任务扫描后按关键词批量筛选
- 提交前 payload 预览与人工确认
- 在非 Windows 或无桌面环境下，验证码图片不会自动弹窗，会提示保存路径以便手动查看

再次强调：不要在未授权的第三方系统上运行。

## Docker 部署（交互式 CLI）

Docker 主要解决两件事：

- 统一 Python 环境与依赖安装
- 在不同机器上快速运行同一套逻辑（仍需你确保合法合规与授权）

### 方式 A：docker run（推荐）

在本目录构建镜像：

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

- 不需要 AI 就不要设置 `SILICONFLOW_API_KEY`，程序会提示并回退到缓存/默认文案。
- 容器里不会自动弹出验证码图片；请按提示到 `runtime/captcha.jpg` 打开查看并手动输入。

### 方式 B：docker compose

```bash
docker compose up --build
```

### Docker 构建失败：无法拉取 python 基础镜像

如果你看到类似错误（无法从 Docker Hub 获取 token/超时）：

- `failed to fetch anonymous token ... auth.docker.io ... timeout`

通常是网络/代理问题。处理建议：

- 确认 Docker Desktop 已配置代理或可直连外网
- 先手动执行 `docker pull python:3.12-slim` 验证能否拉取基础镜像
- 如处于受限网络环境，配置 registry mirror（镜像加速）

## 排障（常见问题）

### 1) 扫描任务时出现 400

可能原因：

- 服务端返回的维度列表包含空维度 ID（导致请求拼出 `dimensionId=None`），或接口策略调整。

当前处理：

- 程序会过滤无效维度，不再请求 `dimensionId=None`。
- `getCircleTask` 兜底扫描只在“按维度扫描未获取到任何任务”时才触发，避免无意义的 400 噪声。

### 2) 看不到验证码弹窗

- Windows：会尝试自动打开图片；若失败会提示保存路径。
- Docker/服务器：不会自动打开，会在日志里提示验证码图片保存路径，请手动打开后输入。

## 安全与合规建议

- 默认使用 mock/桩进行测试，避免真实网络调用。
- 运行前检查 `.gitignore`，确保 `.env`、`config.json`、本地 token、日志、缓存不被提交。
- 若你准备开源发布，请先执行“敏感信息清理”（API Key、Token、身份证号、姓名等）。

## 贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 安全问题反馈

请阅读 [SECURITY.md](SECURITY.md)。

## 免责声明

见 [DISCLAIMER.md](DISCLAIMER.md)。

## 许可证

本项目以 MIT License 发布，见 [LICENSE](LICENSE)。
