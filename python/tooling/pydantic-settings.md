# pydantic-settings

`pydantic-settings` extends [Pydantic](pydantic.md) with `BaseSettings`: a model that reads field values from [environment variables](../../tools/env-vars.md) and `.env` files automatically. Use it for all configuration — API keys, file paths, feature flags, timeouts.

```bash
poetry add pydantic-settings python-dotenv  # python-dotenv enables .env file reading
```

## BaseSettings minimal example

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_key: str           # required — ValidationError at startup if missing
    timeout: int = 30      # optional with default
    debug: bool = False
```

Instantiate once; `Settings()` reads env and `.env`, coerces types, and validates immediately.

## Realistic project Settings

```python
from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    api_key: SecretStr          # hides value in repr/logs
    data_dir: Path = Path("./data")
    output_dir: Path = Path("./output")
    request_timeout: int = 30
    max_retries: int = 3
    log_level: str = "INFO"
    debug: bool = False
```

`.env` file:
```
API_KEY=sk-abc123
DATA_DIR=/home/user/project/data
LOG_LEVEL=DEBUG
```

```python
settings = Settings()
settings.api_key.get_secret_value()  # retrieve SecretStr value
settings.data_dir                    # PosixPath('./data')
settings.request_timeout             # 30  (int, not "30")
```

## Singleton pattern

```python
# config.py
settings = Settings()   # module-level — instantiate once

# everywhere else
from myproject.config import settings
```

## Nested settings

`.env` files are flat (`KEY=value` only — no native nesting). Pydantic-settings reconstructs structure in Python via three strategies.

### Nested BaseModel + `env_nested_delimiter` (recommended)

```python
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseModel):   # plain BaseModel, not BaseSettings
    host: str = "localhost"
    port: int = 5432
    name: str
    password: SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    database: DatabaseSettings
    debug: bool = False
```

`.env`:
```
DATABASE__HOST=db.prod.internal
DATABASE__NAME=myapp
DATABASE__PASSWORD=s3cr3t
```

```python
settings.database.host   # "db.prod.internal"
settings.database.port   # 5432 (int, not "5432")
```

`__` in the env var name means "go one level deeper". `env_nested_delimiter` is not set by default — you must add it.

### JSON-encoded value (one var per section)

```
DATABASE={"host": "localhost", "port": 5432, "name": "myapp", "password": "s3cr3t"}
```

Pydantic detects the model field type and JSON-parses the string automatically. Useful for K8s secrets or CI env blobs; fragile for human-edited `.env` files.

### `dict` field (dynamic keys)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")
    feature_flags: dict[str, bool] = {}
```
```
FEATURE_FLAGS__dark_mode=true
FEATURE_FLAGS__new_onboarding=false
```

Good for feature flags or any open-ended key set.

### Nested settings gotchas

- Sub-models must be `BaseModel`, not `BaseSettings` — nesting two `BaseSettings` doesn't compose as expected.
- With `env_prefix="MYAPP_"` the full key becomes `MYAPP_DATABASE__HOST` (prefix first, then delimiter).

## Env prefix

Namespace all keys to avoid collision with system env vars:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MYAPP_")

    api_key: str    # reads MYAPP_API_KEY
    debug: bool     # reads MYAPP_DEBUG
```

## Priority order (highest → lowest)

1. Constructor arguments: `Settings(api_key="override")`
2. Actual environment variables
3. `.env` file values
4. Field defaults

## Type coercion

| Env string | Field type | Result |
|------------|------------|--------|
| `"30"` | `int` | `30` |
| `"true"` / `"1"` | `bool` | `True` |
| `"/tmp/d"` | `Path` | `PosixPath('/tmp/d')` |
| `'["a","b"]'` or `"a,b"` | `list[str]` | `['a', 'b']` |

## Testing

Constructor args override env/file — inject test values directly:

```python
def test_something():
    s = Settings(api_key="test-key", debug=True)
```

## Refactoring away from global config reads

The singleton `settings` global in `config.py` is fine — it's pure data. The anti-pattern is every other module calling `os.environ.get()` directly, or instantiating stateful dependencies (DB engines, HTTP clients) at module level.

**Before (bad):**
```python
# db.py — two problems: direct env read + instantiation at import time
import os, sqlalchemy
engine = sqlalchemy.create_engine(os.environ.get("DATABASE_URL"))
```

**After (good):**
```python
# db.py
from functools import lru_cache
import sqlalchemy
from .config import settings   # single source of truth

@lru_cache(maxsize=1)
def get_engine() -> sqlalchemy.Engine:
    return sqlalchemy.create_engine(settings.database_url)
```

`@lru_cache` makes `get_engine()` behave like a singleton (creates once, returns cached) while keeping instantiation out of import time. In tests, call `get_engine.cache_clear()` to force a rebuild with different settings.

**FastAPI pattern** — override the settings dependency instead of patching:
```python
# dependencies.py
from functools import lru_cache
from .config import Settings

@lru_cache
def get_settings() -> Settings:
    return Settings()

# in tests
app.dependency_overrides[get_settings] = lambda: Settings(api_key="test")
```

**Rule of thumb:**

| What | Pattern |
|------|---------|
| Config values | One `settings = Settings()` in `config.py` only |
| DB engines, HTTP clients, API wrappers | `@lru_cache` factory — never module-level instantiation |
| FastAPI | `Depends(get_settings)` + `dependency_overrides` in tests |

## Gotchas

- `python-dotenv` not installed → `env_file` silently ignored
- Relative `Path` defaults resolve from the process working directory, not the project root
- `SecretStr` requires `.get_secret_value()` to access the real string
