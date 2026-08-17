# 🤝 贡献指南

感谢你对 **知知 · 企业私有知识库 RAG 问答系统** 感兴趣！本指南帮你快速上手开发并写出符合规范的改动。

## 1. 环境准备

```bash
# 后端依赖（Python 3.10 - 3.13）
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 前端依赖（Node.js 18+）
cd frontend
npm install
```

## 2. 本地开发

```bash
# 后端（默认 8001 端口，热重载）
cd backend && python run.py --reload

# 前端（Vite 开发服务器，/api 代理到 8001）
cd frontend && npm run dev    # http://localhost:5173

# 生成示例文档并构建索引（首次必需）
cd backend && python scripts/init_knowledge.py --generate
```

## 3. 代码规范

| 项 | 约定 |
|----|------|
| Python | PEP 8，行宽 ≤ 100；已有模块保持与周围代码一致 |
| 类型标注 | 公开函数建议类型标注（`from __future__ import annotations`） |
| 前端 | Vue 3 Composition API + `<script setup>` + **TypeScript** |
| 命名 | Python `snake_case`；前端组件 `PascalCase.vue` |
| 注释 | 中文注释，解释「为什么」而非「做了什么」 |

## 4. 提交约定（Conventional Commits）

```
<type>(<scope>): <中文描述>

例如：
feat(pipeline): 新增响应命中缓存
fix(retriever): 修复 RRF 融合重复去重
refactor(llm): 改用 openai 官方 SDK
docs: 补充技术栈文档
test: 新增 BM25 边界用例
```

type 可选：`feat / fix / refactor / docs / test / chore / perf / style`；scope 可选（模块名）。

## 5. 提交前必过清单

```bash
# ① 单元测试（必须全绿，离线可跑）
cd backend && python -m pytest tests/ -v

# ② 后端可导入、应用可创建
cd backend && python -c "from app.main import app; print(app.title)"

# ③ 前端构建无报错（改前端时）
cd frontend && npm run build
```

## 6. 文档同步

改动涉及**行为变化**（接口 / 参数 / 依赖 / 架构）时，请同步更新：

- `README.md`（门面，变更概览）
- `docs/TECH_STACK.md`（新增 / 替换技术）
- `docs/ARCHITECTURE.md`（模块 / 数据流变化）
- `docs/API_REFERENCE.md`（接口契约变化）

新增依赖时，务必更新 `backend/requirements.txt` 与 `docs/TECH_STACK.md` 的版本清单。
