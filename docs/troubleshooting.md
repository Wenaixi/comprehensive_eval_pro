# 故障排查 (Troubleshooting)

本指南列出了常见的运行错误及其解决方案。

## 1. 认证类错误

### 401 Unauthorized
- **原因**: Token 失效或凭证错误。
- **对策**: 系统会自动尝试重登。若持续报错，请检查 `accounts.txt` 中的账号密码。

### 验证码识别失败
- **原因**: AI 额度不足或本地 OCR 环境异常。
- **对策**: 
  1. 检查 `settings.yaml` 中的 API Key。
  2. 确保已安装 `ddddocr` 依赖。

## 2. 资源类错误

### 未匹配到资源包 (No asset matched)
- **原因**: 目录命名不符合五元组规范。
- **对策**: 参考 [资源管理手册](resources.md) 校验目录结构。

### 文件占用
- **原因**: Excel/Word 文件被 Excel 或其他编辑器打开。
- **对策**: 关闭相关编辑器后重试。

## 3. 环境类错误

### ddddocr 安装失败
- **原因**: Python 版本或库依赖冲突。
- **对策**: 
  ```bash
  pip install ddddocr==1.5.6 --no-deps
  pip install onnxruntime
  ```

### 数据库锁定 (SQLite Lock)
- **原因**: 多个实例同时访问 `storage/state.json`。
- **对策**: 确保同一时间内只有一个 CEP 实例运行。

## 4. 日志审计

所有详细错误堆栈均记录在 `logs/` 目录下，排查时请优先查看最新的 `.log` 文件。
