# 后端架构：CQRS + Mediator + Background Worker

readVideo 的 HTTP 后端按功能拆成 Controller、Message、Handler 和基础设施四层。API 地址和 JSON 合同保持不变，但业务逻辑不再写在 FastAPI 路由中。

## 请求流程

查询流程：

```text
Angular -> FastAPI Controller -> Query -> Mediator.send -> QueryHandler -> Store/Service -> JSON
```

命令流程：

```text
Angular -> FastAPI Controller -> Command -> Mediator.send -> CommandHandler -> Store/Service
```

视频处理是耗时命令，采用两阶段分发：

```text
TasksController
  -> StartVideoProcessingCommand
  -> StartVideoProcessingHandler
  -> Redis / RQ
  -> Background Worker
  -> RunVideoProcessingCommand
  -> Mediator.send
  -> RunVideoProcessingHandler
  -> 下载、转录、总结和持久化
```

Controller 只负责 HTTP 参数和文件响应。Handler 负责验证、业务规则和错误语义。Mediator 根据 Command 或 Query 的具体类型找到唯一 Handler，并同时支持同步和异步 Handler。

## 目录职责

- `backend/api/controllers/`：按 tasks、library、reader、watchlist、models、system 拆分的薄 HTTP Controller。
- `backend/application/messages/`：不可变 Command 和 Query 数据对象。
- `backend/application/handlers/`：每种 Message 的业务处理器。
- `backend/application/mediator.py`：统一 `send()` 分发。
- `backend/application/container.py`：Message 与 Handler 的集中注册表。
- `backend/services/`：下载、Whisper、Ollama/MLX、Markdown 和队列等基础服务。
- `backend/storage/`：PostgreSQL/SQLite 持久化实现。

服务内部也遵守信息隐藏：`video_processor` 只编排处理步骤；配置解析、转写引擎、下载进度、
Ollama/MLX 传输、共享本地模型笔记流程、模型输出解析、提取式算法和原文匹配各自拥有唯一模块。公共调用统一经过
`backend.services.notes` 和 `backend.services.transcript_summarizer` 的稳定入口，不依赖私有解析函数。

## Command 与 Query

- Query 只能读取状态，不改变数据库或文件，例如 `ReadMarkdownQuery`、`ListHistoryQuery`。
- Command 表达一次状态变化，例如 `UpdateFavoriteTagsCommand`、`StartVideoProcessingCommand`。
- Query 直接在 API 进程执行；普通短 Command 同步执行；视频等长任务只在 API 中完成排队，由 Worker 执行。
- Handler 抛出 `ApplicationError`，统一转换为稳定的中文 HTTP 错误，不让存储或框架异常泄漏到 Controller。

## 扩展规则

新增功能时先定义 Message，再实现单一 Handler，在 `HANDLER_REGISTRATIONS` 注册，最后添加只调用 `mediator.send(...)` 的 Controller。Controller 不直接导入 `backend.storage` 或 `backend.services`；架构契约测试会阻止业务逻辑重新进入 HTTP 层。

跨层设计与评审规则见 `docs/software-design-principles.md`。
