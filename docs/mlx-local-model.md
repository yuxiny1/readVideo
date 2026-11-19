# Apple Silicon 本地语言模型

readVideo 支持两种 MLX 语言模型服务：

- OMLX：推荐方式。它可以管理多个模型，按请求加载，并提供 OpenAI 兼容 API。
- `mlx_lm.server`：旧的兼容方式，一次启动一个 Hugging Face MLX 模型。

这里的语言模型只负责生成摘要和 Markdown 笔记。音频转文字使用另一套独立的 MLX Whisper，详见 [MLX Whisper 本地转录](mlx-whisper-transcription.md)。

## 推荐：OMLX

### 从零安装

```bash
brew install omlx
brew services start omlx
```

也可以前台运行，方便直接观察日志：

```bash
omlx serve
```

默认服务地址是 `http://127.0.0.1:8000`。管理页面位于：

```text
http://127.0.0.1:8000/admin/dashboard
```

在管理页面下载一个文本生成模型并设为默认。readVideo 示例配置使用：

```text
Qwen2.5-14B-Instruct-4bit
```

模型保存在 `~/.omlx/models/`，不属于 readVideo 仓库，也不会被 Git 提交。

### readVideo 配置

在 `config/.env` 中设置：

```bash
READVIDEO_NOTES_BACKEND=mlx
READVIDEO_MLX_MODEL=Qwen2.5-14B-Instruct-4bit
READVIDEO_MLX_URL=http://127.0.0.1:8000/v1/chat/completions
```

网页中的“笔记生成引擎”可以覆盖 `READVIDEO_NOTES_BACKEND`。因此也可以继续让 Ollama 保持默认，只在某次任务中选择 `MLX（Apple 芯片）`。

### 查询当前 OMLX 模型

```bash
npm run omlx:status
npm run omlx:models
```

或者直接调用 API：

```bash
curl -fsS http://127.0.0.1:8000/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8000/v1/models | python3 -m json.tool
curl -fsS http://127.0.0.1:8000/v1/models/status | python3 -m json.tool
```

`/health` 返回默认模型和已加载模型数量。`/v1/models` 返回已安装模型，`/v1/models/status` 还会显示模型路径、类型、大小和 `loaded` 状态。

OMLX 按需加载模型，所以空闲时看到 `loaded_count: 0` 或 `loaded: false` 是正常状态，不代表模型没有安装。

### 端口说明

OMLX 默认占用 `8000`。readVideo 从 `8000` 开始寻找可用端口，因此 OMLX 已运行时，readVideo 通常会启动在 `http://127.0.0.1:8001`。

不要把 OMLX 直接暴露到公网。它应只绑定 `127.0.0.1`，或由受控的反向代理提供认证。

## 兼容方案：mlx-lm Server

如果不使用 OMLX，可以继续运行单模型服务：

```bash
python3 -m venv ~/mlx-env
~/mlx-env/bin/python -m pip install --upgrade pip mlx-lm huggingface-hub
npm run mlx:serve
```

项目脚本默认使用 `mlx-community/Qwen2.5-72B-Instruct-3bit`，并监听 `127.0.0.1:8080`。对应配置为：

```bash
READVIDEO_NOTES_BACKEND=mlx
READVIDEO_MLX_MODEL=mlx-community/Qwen2.5-72B-Instruct-3bit
READVIDEO_MLX_URL=http://127.0.0.1:8080/v1/chat/completions
```

检查服务：

```bash
curl -fsS http://127.0.0.1:8080/v1/models | python3 -m json.tool
```

终端聊天仍可使用：

```bash
npm run mlx:chat
```

72B 3-bit 模型对 48GB 统一内存已经接近上限。生成长笔记时建议关闭占用大量内存的软件，或改用 OMLX 中较小的 14B/27B 量化模型。

## Docker

Apple MLX 需要在 macOS 原生运行，不能放进 Linux 容器。容器中的 API 和 worker 必须通过 `host.docker.internal` 访问 Mac 上的服务：

```bash
# OMLX
READVIDEO_MLX_URL=http://host.docker.internal:8000/v1/chat/completions

# mlx_lm.server
READVIDEO_MLX_URL=http://host.docker.internal:8080/v1/chat/completions
```

确保 OMLX 或 `mlx_lm.server` 的监听和本机防火墙策略允许容器访问，同时不要开放到不受信任的网络。
