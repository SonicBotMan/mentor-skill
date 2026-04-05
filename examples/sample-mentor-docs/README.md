# Sample 导师文档

这个目录包含一组模拟的导师语料，可以直接用于测试 mentor-skill 的完整 pipeline。

## 使用方式

```bash
# Step 1: 初始化
mentor init --name wang-laoshi --template product

# Step 2: 采集这个目录下的文档
mentor collect --source markdown \
  --input examples/sample-mentor-docs/ \
  --persona wang-laoshi

# Step 3: 检查质量
mentor analyze --persona wang-laoshi --stats

# Step 4: 配置 LLM 并蒸馏
mentor config --set llm.api_key YOUR_KEY
mentor distill --persona wang-laoshi

# Step 5: 生成 Skill
mentor generate --persona wang-laoshi --format all
```

## 文件说明

| 文件 | 内容 |
|------|------|
| `01-product-thinking.md` | 产品思维方法论 |
| `02-user-research.md` | 用户研究框架 |
| `03-feedback-sessions.md` | 模拟对话反馈记录 |
| `04-business-model.md` | 商业模式思考框架 |
| `05-growth-methodology.md` | 用户增长方法论 |
