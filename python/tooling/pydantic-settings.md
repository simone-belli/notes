# pydantic-settings

`pydantic-settings` extends [Pydantic](pydantic.md) with `BaseSettings`: a model that reads field values from environment variables and `.env` files automatically. Use it for all configuration — API keys, file paths, feature flags, timeouts.

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

## Gotchas

- `python-dotenv` not installed → `env_file` silently ignored
- Relative `Path` defaults resolve from the process working directory, not the project root
- `SecretStr` requires `.get_secret_value()` to access the real string
