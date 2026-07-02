import inspect
from typing import Any, Protocol


class RequestHandler(Protocol):
    def handle(self, request: Any) -> Any: ...


class Mediator:
    def __init__(self):
        self._handlers: dict[type, RequestHandler] = {}

    def register(self, request_type: type, handler: RequestHandler) -> None:
        if request_type in self._handlers:
            raise ValueError(f"请求类型已注册：{request_type.__name__}")
        self._handlers[request_type] = handler

    async def send(self, request: Any) -> Any:
        handler = self._handlers.get(type(request))
        if handler is None:
            raise LookupError(f"没有为 {type(request).__name__} 注册处理器。")
        result = handler.handle(request)
        return await result if inspect.isawaitable(result) else result
