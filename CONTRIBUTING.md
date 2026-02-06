# 贡献指南

感谢你愿意贡献。

## 基本原则

- 所有改动必须遵守合规与“仅供学习研究”边界，不接受任何明显增强未授权访问能力的改动。
- 不提交任何敏感信息：账号、密码、Token、身份证号、真实姓名、API Key、真实接口返回数据等。
- 提交前确保测试通过。

## 开发环境

```bash
python -m venv .venv
.\\.venv\\Scripts\\activate
pip install -r requirements.txt
```

## 测试

```bash
python -m unittest -q
```

## 提交规范

- 优先保持现有结构（services/utils 分层）。
- 变更需要配套单元测试。
- 如涉及配置项，更新 `config.example.json` 与 README 的配置说明。
