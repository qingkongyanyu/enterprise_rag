# API 参考

统一前缀：`/api/v1`；统一响应包裹：`{ "code": 0, "message": "ok", "data": {...} }`。

- `code == 0` 表示成功；非 0 表示失败（HTTP 状态码一致）。
- 交互式文档：启动后访问 `http://localhost:8001/api/docs`。

## 1. 对话

### 非流式问答

```
POST /api/v1/chat
```

请求体：

```json
{ "question": "员工请假流程是什么？", "session_id": null }
```

`session_id` 可省略，服务端自动生成。

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "answer": "员工请假流程如下：[1] ...",
    "session_id": "sess_abc123",
    "sources": [
      { "source": "人事_04.txt", "chunk_id": "人事_04.txt::0", "score": 1.0, "snippet": "员工请假管理制度...", "rank": 1 }
    ],
    "elapsed_ms": 1562,
    "grounded": true
  }
}
```

### 流式问答（SSE）

```
POST /api/v1/chat/stream
```

请求体同上。响应为 `text/event-stream`，每行 `data: {json}`，事件类型：

| type | 字段 | 说明 |
| --- | --- | --- |
| `meta` | `session_id` | 会话 ID |
| `delta` | `text` | 增量文本（逐 token） |
| `sources` | `sources[]` | 引用来源 |
| `done` | `elapsed_ms` | 结束 |
| `error` | `message` | 错误 |

```bash
curl -N -X POST http://localhost:8001/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"差旅住宿标准是多少？"}'
```

## 2. 知识库

### 概览

```
GET /api/v1/knowledge/documents
```

返回文档列表、分类统计、索引状态。

### 构建 / 重建索引

```
POST /api/v1/knowledge/rebuild
```

```json
{
  "code": 0,
  "message": "ok",
  "data": { "doc_count": 20, "chunk_count": 22, "elapsed_ms": 120, "cached_chunks": 22 }
}
```

### 上传文档

```
POST /api/v1/knowledge/upload     (multipart/form-data, 字段名 file)
```

仅支持 `.txt` / `.md`，单文件 ≤ 5MB。上传成功后自动重建索引。

### 删除文档

```
DELETE /api/v1/knowledge/documents/{文件名}
```

删除后自动重建索引。

## 3. 会话

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/sessions` | 会话列表（按最后活跃倒序） |
| GET | `/api/v1/sessions/{id}/history` | 会话历史 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话 |
| DELETE | `/api/v1/sessions` | 清空全部会话 |

## 4. 系统

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康探针 |
| GET | `/api/v1/system/stats` | 系统状态（版本/索引/模型/配置，脱敏） |
| GET | `/api/v1/system/metrics` | 运行指标（对话数/平均耗时/缓存命中） |

```json
GET /api/v1/system/stats
{
  "code": 0,
  "message": "ok",
  "data": {
    "app_version": "2.0.0",
    "index_ready": true,
    "doc_count": 20,
    "chunk_count": 22,
    "embedding_model": "BAAI/bge-small-zh",
    "llm_configured": true,
    "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "llm_model": "qwen-turbo",
    "final_top_k": 5,
    "enable_rerank": false
  }
}
```

## 5. 错误码约定

| HTTP | code | 含义 |
| --- | --- | --- |
| 400 | 400 | 请求错误（如空问题） |
| 404 | 404 | 资源不存在 |
| 409 | 409 | 冲突（如重复文档） |
| 422 | 422 | 参数校验失败 |
| 502 | 502 | 上游 LLM 调用失败 |
| 503 | 503 | 依赖未就绪（索引未构建 / LLM 未配置） |
| 500 | 500 | 服务器内部错误 |
