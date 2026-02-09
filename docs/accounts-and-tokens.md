# 批量账号与会话（Token）

## 1) 批量账号文件在哪？

- 默认：项目目录下的 `accounts.txt`
- 模板：`accounts.example.txt`
- 可通过环境变量覆盖默认路径：`CEP_ACCOUNTS_FILE`

格式：每行 `学号 空格 密码`；支持空行与 `#` 注释行。

## 2) Token 如何持久化？

程序会把每个账号的 `token` 和 `user_info` 存在 `config.json` 的 `accounts` 字段里（按学号索引），示意：

```json
{
  "accounts": {
    "20260001": { "token": "...", "user_info": { } },
    "20260002": { "token": "...", "user_info": { } }
  }
}
```

## 3) 批量模式登录顺序

对账号文件里所有账号，程序会先做“预登录/持久化”，再让你选择要处理哪些账号：

1. 读取该账号的持久化 token，尝试激活会话并拉任务列表验证
2. token 有效：标记为“已就绪”
3. token 无效/不存在：使用账号文件里的密码登录
   - 若安装了 `ddddocr` 则自动识别验证码
   - 否则会保存验证码图片并提示你手动输入验证码
4. 登录成功：把 token 与 user_info 写入 `config.json`，标记为“已就绪”
5. 预登录结束后展示账号列表（含姓名/Token/状态），支持多选（全选/反选/追加/移除）
6. 后续任务操作只会应用到你选中的账号集合

## 4) 无人值守批量跑（可选）

把默认任务选择与自动提交开关写进 `.env`：

- `CEP_DEFAULT_TASK_MODE=y`：默认跑四大专项
- `CEP_AUTO_MODE=1`：默认跳过预览直接提交
- `CEP_AUTO_CONFIRM_RESUBMIT=1`：默认确认重交

更多变量解释见 `.env.example`。
