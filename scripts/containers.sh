#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

export READVIDEO_UID=${READVIDEO_UID:-$(id -u)}
export READVIDEO_GID=${READVIDEO_GID:-$(id -g)}

compose() {
    if [ -f .container-env ]; then
        docker compose --env-file .container-env -f compose.yml "$@"
    else
        docker compose -f compose.yml "$@"
    fi
}

compose_gpu() {
    if [ -f .container-env ]; then
        docker compose --env-file .container-env -f compose.yml -f compose.gpu.yml "$@"
    else
        docker compose -f compose.yml -f compose.gpu.yml "$@"
    fi
}

compose_host_ollama() {
    if [ -f .container-env ]; then
        docker compose --env-file .container-env -f compose.yml -f compose.host-ollama.yml "$@"
    else
        docker compose -f compose.yml -f compose.host-ollama.yml "$@"
    fi
}

command=${1:-help}
case "$command" in
    up)
        compose up -d --build
        ;;
    up-gpu)
        compose_gpu up -d --build
        ;;
    up-host-ollama)
        compose_host_ollama up -d --build
        ;;
    management)
        compose --profile management up -d
        ;;
    down)
        compose down
        ;;
    logs)
        compose logs -f --tail=200
        ;;
    ps)
        compose ps
        ;;
    migrate)
        if [ ! -f readvideo.sqlite3 ]; then
            printf '%s\n' "找不到 readvideo.sqlite3，无法执行迁移。" >&2
            exit 1
        fi
        compose --profile migration run --rm migrate
        ;;
    pull-model)
        model=${2:-qwen2.5:32b}
        compose exec ollama ollama pull "$model"
        ;;
    backup)
        mkdir -p backups
        backup_path="backups/readvideo-$(date +%Y%m%d-%H%M%S).sql"
        compose exec -T postgres pg_dump -U readvideo -d readvideo > "$backup_path"
        printf '数据库备份已写入 %s\n' "$backup_path"
        ;;
    *)
        printf '%s\n' "用法：$0 {up|up-gpu|up-host-ollama|management|down|logs|ps|migrate|pull-model [模型]|backup}"
        ;;
esac
