# Python — Language / Runtime

| File | Type | Description |
|------|------|-------------|
| [asyncio.md](asyncio.md) | note | async def, await, asyncio.run(), gather(), create_task() — core mechanics |
| [cli.md](cli.md) | ref | Running Python from the terminal: `-c`, `-m`, scripts |
| [concurrency.md](concurrency.md) | note | GIL, threading, multiprocessing, asyncio — overview and decision guide |
| [context-managers.md](context-managers.md) | note | `with` statement, class-based and `@contextmanager` |
| [datetime.md](datetime.md) | note | datetime from strings and integer timestamps; timezone awareness; strptime, fromisoformat, fromtimestamp |
| [import-system.md](import-system.md) | note | Modules, packages, `__init__.py`, `sys.path`, public API |
| [logging.md](logging.md) | note | stdlib logging: pipeline, levels, dictConfig, best practices, structured logging |
| [threading.md](threading.md) | note | `ThreadPoolExecutor`, `Future` mechanics, `as_completed`, exception handling, shared state |

## Structure

runtime/\
├── [asyncio.md](asyncio.md)\
├── [cli.md](cli.md)\
├── [concurrency.md](concurrency.md)\
├── [context-managers.md](context-managers.md)\
├── [datetime.md](datetime.md)\
├── [import-system.md](import-system.md)\
├── [logging.md](logging.md)\
└── [threading.md](threading.md)
