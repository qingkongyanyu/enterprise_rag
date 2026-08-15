# 开发指南

## 环境准备

```bash
# 后端
cd backend
pip install -r requirements-dev.txt

# 前端
cd frontend
npm install
```

## 常用命令

```bash
# 启动后端（默认 8000）
cd backend && python run.py

# 启动后端（热重载开发）
cd backend && python run.py --reload

# 前端开发服务器（5173，/api 代理到 8000）
cd frontend && npm run dev

# 前端类型检查 + 生产构建
cd frontend && npm run build

# 运行后端测试
cd backend && python -m pytest tests/ -v
```

## 测试

测试全部使用**确定性替身**（FakeEmbedder / FakeLLM），不依赖网络与真实模型，可离线运行。

```bash
cd backend && python -m pytest tests/ -v
```

覆盖范围：

| 文件 | 覆盖 |
| --- | --- |
| `tests/test_chunking.py` | 分块边界、重叠、空块过滤、元数据 |
| `tests/test_bm25.py` | 中文分词、相关性排序、空查询 |
| `tests/test_retriever.py` | 混合检索排序、精确词召回、得分归一化 |
| `tests/test_api.py` | 全 API 流程（构建/问答/流式/上传/删除/会话） |

## 代码结构速览

```
backend/app/
├── api/            # 路由：只做参数绑定与响应
├── core/           # config / logging / exceptions
├── models/         # Pydantic schemas + 领域结构 Chunk
├── services/       # 业务核心，全部可单测
│   ├── chunking.py     # 分块（纯函数，易测）
│   ├── bm25.py         # BM25 稀疏检索（自实现）
│   ├── embeddings.py   # 向量化 + 磁盘缓存
│   ├── vector_store.py # FAISS 封装
│   ├── retriever.py    # 混合检索 + RRF
│   ├── pipeline.py     # RAG 编排（核心）
│   └── ...
└── utils/          # 文本 / 缓存工具
```

## 代码风格约定

- 全部中文注释；公共函数带 docstring。
- 类型注解：函数参数与返回值尽量标注。
- 异常：业务异常继承 `AppError`，由统一 handler 处理，不要在路由里散落 try/except。
- 配置：新增可调项一律进 `Settings`（`core/config.py`），同步更新 `.env.example`。

## 提交规范

- 建议使用 Conventional Commits：`feat: xxx` / `fix: xxx` / `docs: xxx` / `test: xxx`。
- 提交前确认 `.env`、`data/vector_store`、`data/embedding_cache` 等未入库。
