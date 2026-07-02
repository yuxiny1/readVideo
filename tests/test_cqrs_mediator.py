import inspect
import unittest
from dataclasses import dataclass
from pathlib import Path

from backend.application.messages import library, models, reader, system, tasks, watchlist
from backend.application.container import HANDLER_REGISTRATIONS, get_mediator
from backend.application.mediator import Mediator


@dataclass(frozen=True)
class ExampleQuery:
    value: int


class SyncHandler:
    def handle(self, query: ExampleQuery) -> int:
        return query.value * 2


class AsyncHandler:
    async def handle(self, query: ExampleQuery) -> int:
        return query.value + 1


class MediatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_dispatches_sync_and_async_handlers(self):
        sync_mediator = Mediator()
        sync_mediator.register(ExampleQuery, SyncHandler())
        async_mediator = Mediator()
        async_mediator.register(ExampleQuery, AsyncHandler())

        self.assertEqual(await sync_mediator.send(ExampleQuery(3)), 6)
        self.assertEqual(await async_mediator.send(ExampleQuery(3)), 4)

    async def test_rejects_unregistered_requests(self):
        with self.assertRaisesRegex(LookupError, "没有为 ExampleQuery 注册处理器"):
            await Mediator().send(ExampleQuery(1))

    async def test_rejects_duplicate_handler_registration(self):
        mediator = Mediator()
        mediator.register(ExampleQuery, SyncHandler())

        with self.assertRaisesRegex(ValueError, "请求类型已注册"):
            mediator.register(ExampleQuery, SyncHandler())

    async def test_application_container_registers_every_request_once(self):
        request_types = [request_type for request_type, _handler in HANDLER_REGISTRATIONS]
        message_types = {
            message_type
            for module in (library, models, reader, system, tasks, watchlist)
            for name, message_type in inspect.getmembers(module, inspect.isclass)
            if name.endswith(("Command", "Query")) and message_type.__module__ == module.__name__
        }

        self.assertEqual(len(request_types), len(set(request_types)))
        self.assertEqual(set(request_types), message_types)
        self.assertIs(get_mediator(), get_mediator())


class CqrsArchitectureContractTests(unittest.TestCase):
    def test_controllers_only_send_messages_through_the_mediator(self):
        controller_dir = Path(__file__).resolve().parents[1] / "backend" / "api" / "controllers"
        controllers = [path for path in controller_dir.glob("*_controller.py")]

        self.assertGreaterEqual(len(controllers), 6)
        for controller in controllers:
            source = controller.read_text(encoding="utf-8")
            self.assertIn("get_mediator().send", source, controller.name)
            self.assertNotIn("backend.storage", source, controller.name)
            self.assertNotIn("backend.services", source, controller.name)

    def test_background_worker_dispatches_a_command_through_the_mediator(self):
        task_queue = (
            Path(__file__).resolve().parents[1] / "backend" / "services" / "task_queue.py"
        ).read_text(encoding="utf-8")

        self.assertIn("RunVideoProcessingCommand", task_queue)
        self.assertIn("get_mediator().send", task_queue)


if __name__ == "__main__":
    unittest.main()
