# MLX 本地模型

## 三种使用方式

模型只需要下载一次，文件保存在 Hugging Face 缓存中，不属于 readVideo 仓库。

直接在终端聊天：

```bash
npm run mlx:chat
```

第一次运行会继续下载尚未完成的分片。下载完成后，同一条命令会加载模型并进入对话。

让 readVideo 调用模型：

```bash
npm run mlx:serve
```

保持这个终端运行，然后启动 readVideo。在“新视频”页面把“笔记生成引擎”改为“MLX（Apple 芯片）”。页面会检查 `http://127.0.0.1:8080/v1/models`，确认服务已启动且所选模型存在于本地缓存后才提交任务。

直接检查服务：

```bash
curl http://127.0.0.1:8080/v1/models
```

## 当前模型是否下载完成

查看缓存大小和未完成分片：

```bash
du -sh ~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-72B-Instruct-3bit
find ~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-72B-Instruct-3bit -name '*.incomplete'
```

第二条命令没有输出，才表示没有残留的未完成分片。下载中断时重新运行 `npm run mlx:chat` 即可复用缓存并继续下载，不会从头开始。

## readVideo 配置

本机直接运行 FastAPI 时使用：

```bash
READVIDEO_NOTES_BACKEND=mlx
READVIDEO_MLX_MODEL=mlx-community/Qwen2.5-72B-Instruct-3bit
READVIDEO_MLX_URL=http://127.0.0.1:8080/v1/chat/completions
```

网页中的引擎选择会覆盖默认的 `READVIDEO_NOTES_BACKEND`。因此也可以继续保留 Ollama 为默认，只在需要 72B 模型时选择 MLX。

使用 Docker Compose 时，API 和 Worker 会通过 `host.docker.internal:8080` 访问 Mac 上原生运行的 MLX 服务。MLX 仍然在 macOS 上使用 Metal，不会被装入 Linux 容器。

## 内存建议

72B 3-bit 对 48GB 统一内存已经比较接近上限。首次加载和生成长笔记时，建议关闭占用大量内存的浏览器标签、Docker 工作负载和 IDE。`npm run mlx:serve` 已把提示缓存数量限制为 1，并使用较小的预填充分块；如果仍然发生内存压力，可以先减少同时运行的软件，或把服务的 `--max-tokens` 调低到 `2048`。

MLX 服务只绑定 `127.0.0.1`。它是本地开发服务，不应直接暴露到公网。
