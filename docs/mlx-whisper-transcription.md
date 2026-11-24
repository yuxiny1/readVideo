# MLX Whisper 本地转录

readVideo 在 Apple Silicon 上支持 `mlx-whisper`，并默认推荐 Hugging Face 上的
`mlx-community/whisper-large-v3-mlx`。它使用完整 Whisper large-v3 权重，约 3.1GB，
适合中文课程、中英混合内容、访谈和需要高准确度的长视频。

## 模型选择

| 模型 | 大小 | 用途 |
| --- | --- | --- |
| `mlx-community/whisper-large-v3-mlx` | 约 3.1GB | 完整大型 v3，高精度默认值 |
| `mlx-community/whisper-large-v3-turbo` | 约 1.6GB | 更快、更省内存的回退选项 |

Hugging Face 上较新的 `*-asr-fp16` 仓库使用 `mlx-audio` 格式，但仍然是 large-v3
模型家族，并不是更新、更准确的 Whisper 权重。当前应用采用 Apple MLX Examples
维护的 `mlx-whisper` 路径，因为它对长音频、语言提示和现有任务管线更成熟。

## 安装

MLX 必须运行在 Apple Silicon Mac 上。项目沿用用于 MLX-LM 的独立环境：

```bash
python3 -m venv ~/mlx-env
source ~/mlx-env/bin/activate
python -m pip install -U pip mlx-lm mlx-whisper
```

也可以使用项目脚本：

```bash
npm run mlx:whisper:install
npm run mlx:whisper:download
```

模型保存在 `~/.cache/huggingface/hub`，不会写入仓库。首次在网页点击“下载”时，
后端也会下载所选 MLX Whisper 模型。

## 配置

```bash
READVIDEO_TRANSCRIPTION_BACKEND=mlx
READVIDEO_MLX_WHISPER_PYTHON=~/mlx-env/bin/python
READVIDEO_MLX_WHISPER_MODEL=mlx-community/whisper-large-v3-mlx
READVIDEO_LOCAL_WHISPER_LANGUAGE=auto
```

MLX Whisper 负责音频转文字；`READVIDEO_MLX_MODEL` 对应的 MLX-LM 模型负责总结，
两者是不同模型，也不需要启动同一个服务。转录由后台 worker 直接启动独立 MLX
进程，因此不需要运行 `mlx_lm.server`。

## 防重复策略

Whisper 的序列到序列结构可能产生重复或幻觉。MLX 转录路径采用以下设置：

- 使用完整 large-v3 模型；
- 不把上一音频窗口的预测文本强制带入下一窗口；
- 使用温度回退和更严格的压缩比阈值；
- 按转录片段删除相邻的完全重复内容；
- 继续使用语音频段过滤和响度标准化。

这些设置会显著降低连续重复，但语音识别仍可能受录音质量、背景音乐、多人重叠
说话和专业术语影响。已知语言时可以在网页中明确选择 `zh` 或 `en`。

## 容器

Apple MLX 不能在 Linux 容器中运行。Compose 的 API 和 worker 继续使用
`whisper.cpp` 与挂载的 GGML 模型；本机运行 readVideo 时可以选择 MLX Whisper。

`whisper.cpp` 兼容路径会把长录音按完整窗口转录，避免单次处理一小时直播时静默遗漏中后段：

```bash
READVIDEO_LOCAL_WHISPER_CHUNK_SECONDS=300
```

每个 5 分钟窗口都成功并通过 JSON 时间戳审计后，才会原子合并并写入最终 TXT 与 `*_transcription.audit.json`。任一窗口失败、时间戳损坏或覆盖不连续时，任务会明确失败，不会覆盖已有完整 TXT，也不会把半成品标为完成。历史中的本地转录如果没有有效审计，会自动重新转录。

Whisper 的一句话可以合法跨过 5 分钟边界，系统会记录超出的毫秒数并把审计范围截到当前窗口，不会因此误报失败。真正失败时，已经验证的分块和配置指纹 checkpoint 会保留；对同一视频重试会从第一个未完成分块继续，成功合并后再清理 checkpoint。
