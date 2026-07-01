import json
import os
from datetime import datetime
from typing import Any, MutableMapping, Optional


TASK_KEY_PREFIX = "readvideo:task:"
TASK_INDEX_KEY = "readvideo:tasks"
DEFAULT_TASK_TTL_SECONDS = 60 * 60 * 24 * 30


class TaskRepository:
    def __init__(self, memory: MutableMapping[str, dict[str, Any]]):
        self.memory = memory

    def get(self, task_id: str) -> Optional[dict[str, Any]]:
        client = self._redis_client()
        if client is not None:
            payload = client.get(f"{TASK_KEY_PREFIX}{task_id}")
            if payload:
                task = json.loads(payload)
                self.memory[task_id] = task
                return task
            self.memory.pop(task_id, None)
            client.zrem(TASK_INDEX_KEY, task_id)
            return None
        return self.memory.get(task_id)

    def save(self, task: dict[str, Any]) -> None:
        task_id = str(task["task_id"])
        self.memory[task_id] = task
        client = self._redis_client()
        if client is None:
            return
        score = datetime.fromisoformat(str(task["updated_at"])).timestamp()
        payload = json.dumps(task, ensure_ascii=False)
        ttl = int(os.getenv("READVIDEO_TASK_TTL_SECONDS", str(DEFAULT_TASK_TTL_SECONDS)))
        with client.pipeline() as pipeline:
            pipeline.set(f"{TASK_KEY_PREFIX}{task_id}", payload, ex=ttl)
            pipeline.zadd(TASK_INDEX_KEY, {task_id: score})
            pipeline.execute()

    def list(self) -> list[dict[str, Any]]:
        client = self._redis_client()
        if client is None:
            return sorted(self.memory.values(), key=lambda task: task.get("updated_at", ""), reverse=True)

        task_ids = client.zrevrange(TASK_INDEX_KEY, 0, 999)
        if not task_ids:
            return []
        payloads = client.mget([f"{TASK_KEY_PREFIX}{task_id}" for task_id in task_ids])
        stale_ids = [task_id for task_id, payload in zip(task_ids, payloads) if not payload]
        if stale_ids:
            client.zrem(TASK_INDEX_KEY, *stale_ids)
            for task_id in stale_ids:
                self.memory.pop(task_id, None)
        tasks = [json.loads(payload) for payload in payloads if payload][:200]
        for task in tasks:
            self.memory[str(task["task_id"])] = task
        return tasks

    def clear(self) -> None:
        self.memory.clear()
        client = self._redis_client()
        if client is None:
            return
        task_ids = client.zrange(TASK_INDEX_KEY, 0, -1)
        keys = [f"{TASK_KEY_PREFIX}{task_id}" for task_id in task_ids]
        if keys:
            client.delete(*keys)
        client.delete(TASK_INDEX_KEY)

    @staticmethod
    def _redis_client():
        redis_url = os.getenv("READVIDEO_REDIS_URL", "").strip()
        if not redis_url:
            return None
        from redis import Redis

        return Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)
