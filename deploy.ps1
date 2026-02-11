# Comprehensive Eval Pro (CEP) - 一键部署脚本
# 适用环境: Windows PowerShell

$ErrorActionPreference = "Stop"

function Write-Host-Color ($msg, $color = "Cyan") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" -ForegroundColor $color
}

Write-Host-Color "🚀 开始部署 Comprehensive Eval Pro (CEP) 系统..." "Yellow"

# 1. 环境自检
Write-Host-Color "🔍 正在检查 Docker 环境..."
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host-Color "❌ 错误: 未找到 Docker，请先安装 Docker Desktop (https://www.docker.com/products/docker-desktop/)" "Red"
    exit
}

# 2. 初始化配置文件
Write-Host-Color "📁 正在检查本地数据结构..."

# 创建必要的目录
$dirs = @("configs", "assets", "runtime")
foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host-Color "  └─ 已创建目录: $dir"
    }
}

# 初始化配置文件 (如果不存在)
if (!(Test-Path "configs/settings.yaml")) {
    Copy-Item "configs.example/settings.example.yaml" "configs/settings.yaml"
    Write-Host-Color "  └─ 已初始化 configs/settings.yaml (请稍后编辑 API Key)" "Green"
}

if (!(Test-Path "configs/state.json")) {
    Copy-Item "configs.example/state.example.json" "configs/state.json"
    Write-Host-Color "  └─ 已初始化 configs/state.json" "Green"
}

if (!(Test-Path "accounts.txt")) {
    Copy-Item "accounts.example.txt" "accounts.txt"
    Write-Host-Color "  └─ 已初始化 accounts.txt (请稍后填入账号密码)" "Green"
}

# 3. 构建并运行
Write-Host-Color "🏗️ 正在构建镜像并启动容器 (首次运行可能较慢)..."
docker-compose up -d --build

Write-Host-Color "✅ 部署完成！" "Green"
Write-Host-Color "-------------------------------------------------------" "White"
Write-Host-Color "💡 后续操作指引:" "Cyan"
Write-Host-Color "1. 请编辑 'configs/settings.yaml' 填入您的 SiliconFlow API Key。" "White"
Write-Host-Color "2. 请编辑 'accounts.txt' 填入需要处理的学号与密码。" "White"
Write-Host-Color "3. 运行以下命令进入交互式界面进行任务操作:" "Yellow"
Write-Host-Color "   docker attach cep-system" "Green"
Write-Host-Color "-------------------------------------------------------" "White"
Write-Host-Color "提示: 按 Ctrl+P, Ctrl+Q 可在不停止容器的情况下退出 attach 模式。" "Gray"
