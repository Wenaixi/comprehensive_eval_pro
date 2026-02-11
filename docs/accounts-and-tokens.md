# 🔑 账户与会话管理

CEP 支持大规模账户的批量管理与状态持久化。

---

## 📝 1. 批量账号配置

- **默认文件**: `accounts.txt` (位于项目根目录)。
- **模板参考**: `accounts.example.txt`。
- **自定义路径**: 在 `configs/settings.yaml` 中通过 `accounts_file` 指定。

### 格式要求
每行一个账号，格式为 `学号 密码`，中间用空格分隔：
```text
G350181200912110035 689050
# 支持以 # 开头的注释
G350181200912110036 123456
```

---

## 💾 2. Token 持久化机制

为了减少登录频率并规避验证码风险，系统会自动将登录成功的 Token 持久化到 `configs/state.json`。

### 状态存储结构
```json
{
  "accounts": {
    "学号": {
      "token": "JWT_TOKEN_HERE",
      "user_info": { "name": "张三", "school": "..." },
      "last_update": "2026-02-11T..."
    }
  }
}
```

---

## 🔄 3. 预登录流程 (Pre-Login)

每次启动程序，CEP 都会执行以下“究极”预登录逻辑：

1. **缓存检测**: 检查 `state.json` 中是否有该账号的 Token。
2. **有效性验证**: 携带 Token 尝试拉取任务列表。
3. **静默复用**: 若 Token 有效，标记为“已就绪”，跳过登录。
4. **自动重连**: 若 Token 失效，使用 `accounts.txt` 中的密码执行登录，并更新缓存。

---

## 🤖 4. 无人值守模式 (Headless Mode)

如果你希望全自动运行，可以在 `configs/settings.yaml` 中开启以下选项：

```yaml
# 自动模式开关
auto_mode: true              # 跳过预览，直接提交
auto_confirm_resubmit: true  # 自动确认重交
default_task_mode: "y"       # 默认运行四大专项任务
```
