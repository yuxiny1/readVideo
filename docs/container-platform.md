# 容器平台

readVideo 使用 Docker Compose 运行完整平台：Angular + Nginx、FastAPI、RQ Worker、PostgreSQL、Redis、Ollama 和 Portainer。它适合单机开发，也适合部署到带 NVIDIA GPU 的 Azure Linux VM。当前工作负载包含本地大模型、Whisper、大文件和长任务，单台 GPU VM 比 Kubernetes 或 Azure Container Apps 更简单、成本更可控。

## 首次启动

需要 Docker Desktop，或安装了 Docker Engine、Compose 插件与 NVIDIA Container Toolkit 的 Linux VM。

```bash
cp deploy/container.env.example .container-env
npm run containers:up
npm run containers:migrate
npm run containers:pull-model -- qwen2.5:32b
```

在 macOS 上，Docker Desktop 无法使用 Apple Metal，而且原生 Ollama 通常已经有模型。推荐改用下面的启动命令，让容器化 API 与 Worker 连接宿主机 Ollama，避免重复下载模型并保留 Metal 加速：

```bash
npm run containers:up:host-ollama
```

标准 `containers:up` 使用容器内 Ollama。本机已有的原生模型不会自动复制到容器中；容器模型保存在独立的 `ollama-data` volume，第一次需要执行 `containers:pull-model`。`qwen2.5:32b` 约 20GB；硬件不足时可显式选择 `qwen2.5:14b`，不要静默降级。

服务入口：

- 应用：`http://localhost:8080`
- API：`http://localhost:8001`
- 就绪状态：`http://localhost:8080/health/ready`
- Portainer：`https://localhost:9443`
- Ollama：`http://localhost:11435`
- pgAdmin：运行 `npm run containers:management` 后访问 `http://localhost:5050`

Portainer 第一次打开时会要求创建管理员账号。pgAdmin 连接地址使用 `postgres`，端口 `5432`，数据库和用户名均为 `readvideo`。

## 日常操作

```bash
npm run containers:ps
npm run containers:logs
npm run containers:backup
npm run containers:down
```

`http://localhost:11435` 始终是容器 Ollama 的管理入口；使用 macOS 宿主机模式时，实际笔记请求发送到宿主机的 `http://localhost:11434`。

下载视频、转录文本和 Markdown 笔记仍保存在仓库的 `downloads/`、`models/`、`notes/` 中。数据库、队列、Ollama 模型和管理面板数据使用 Docker volumes，`containers:down` 不会删除它们。不要使用 `docker compose down -v`，除非明确要清空全部平台数据。

## Azure GPU VM

生产环境建议 Ubuntu LTS、独立托管数据盘和具备足够显存的 NVIDIA GPU VM。安装 NVIDIA 驱动、NVIDIA Container Toolkit、Docker Engine 与 Compose 后：

```bash
git clone <repository-url> readVideo
cd readVideo
cp deploy/container.env.example .container-env
npm run containers:up:gpu
npm run containers:migrate
npm run containers:pull-model -- qwen2.5:32b
```

把 `downloads/`、`notes/`、`models/` 与 Docker data root 放在持久化数据盘。公网只开放反向代理的 `80/443`；Portainer `9443` 应限制到管理 IP 或 VPN。不要直接公开 PostgreSQL、Redis、API 或 Ollama 端口。生产密码只放在 `.container-env`，并定期执行 `npm run containers:backup` 后把备份复制到 Azure Blob Storage。

## 数据迁移

`npm run containers:migrate` 会把根目录 `readvideo.sqlite3` 的 history、favorites、folders、watchlist、tags 与关联表幂等迁移到 PostgreSQL。重复执行不会生成重复记录。迁移前后可用下面的接口确认：

```bash
curl http://localhost:8080/api/history
curl http://localhost:8080/health/ready
```
