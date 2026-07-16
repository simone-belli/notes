---
tags:
  - performance
---

# File I/O

Python's built-in `open()` returns a file object. Always wrap it in a [`with` statement](context-managers.md) so the file is closed even if an exception occurs.

```python
with open('data.txt', 'r', encoding='utf-8') as f:
    content = f.read()
```

## Modes

| mode | meaning |
|------|---------|
| `'r'` | read text (default) |
| `'w'` | write text — **truncates** existing file |
| `'a'` | append text — writes at end, creates if absent |
| `'x'` | exclusive create — fails if file exists |
| `'rb'` / `'wb'` | read / write binary |
| `'r+'` | read + write, no truncate |

Append `'b'` for binary mode; it skips encoding and line-ending translation.

!!! warning "`'w'` truncates silently"
    If you need to update an existing file, use `'r+'` (or `'a'` to append). `'w'` destroys the existing content with no prompt.

Always pass `encoding='utf-8'` for text files — the default is platform-dependent.

## Text patterns

```python
# whole file
with open('file.txt', encoding='utf-8') as f:
    text = f.read()

# list of lines (each includes '\n')
with open('file.txt', encoding='utf-8') as f:
    lines = f.readlines()

# line-by-line (memory-efficient)
with open('file.txt', encoding='utf-8') as f:
    for line in f:
        process(line.rstrip('\n'))

# write
with open('out.txt', 'w', encoding='utf-8') as f:
    f.write('hello\n')
    f.writelines(['line1\n', 'line2\n'])   # no separator added
```

## Binary patterns

```python
# read entire file
with open('image.png', 'rb') as f:
    data = f.read()          # bytes

# stream in chunks (large files)
with open('bigfile.dat', 'rb') as f:
    while chunk := f.read(4096):
        process(chunk)

# write
with open('out.bin', 'wb') as f:
    f.write(b'\x00\xff')
```

## Random access: `seek()` / `tell()`

```python
with open('data.bin', 'rb') as f:
    f.seek(100)       # move cursor to byte 100 from start
    f.seek(-10, 1)    # 10 bytes before current position
    f.seek(0, 2)      # move to end
    pos = f.tell()    # current byte offset
```

`whence`: `0` = start (default), `1` = current, `2` = end.

!!! note "Text mode seek"
    In text mode, `seek(n)` is only reliable with `n=0` (start) or a value previously returned by `tell()`. Encoding makes arbitrary byte offsets invalid.

## CSV

Use the `csv` module — it handles quoting, escaping, and delimiters.

```python
import csv

# read (dict per row)
with open('data.csv', newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        print(row['name'])

# write (dict rows)
with open('out.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'age'])
    writer.writeheader()
    writer.writerow({'name': 'Alice', 'age': 30})
```

Pass `newline=''` to `open()` — `csv` manages line endings itself.

## JSON

```python
import json

with open('config.json', encoding='utf-8') as f:
    data = json.load(f)

with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
```

`json.loads` / `json.dumps` operate on strings; `json.load` / `json.dump` operate on file objects.

## Pickle

```python
import pickle

with open('model.pkl', 'wb') as f:
    pickle.dump(obj, f)

with open('model.pkl', 'rb') as f:
    obj = pickle.load(f)
```

!!! warning "Security"
    Never unpickle data from an untrusted source — loading a pickle file executes arbitrary Python code.

## `pathlib.Path` shortcuts

[`pathlib.Path`](pathlib.md) objects can be passed to `open()` directly, and also expose convenience methods for simple one-shot reads/writes:

```python
from pathlib import Path

p = Path('data/readme.txt')
text = p.read_text(encoding='utf-8')
p.write_text('hello\n', encoding='utf-8')

raw = p.read_bytes()
p.write_bytes(b'\x00\xff')
```

Use `open()` when you need streaming, mode flags, or partial reads.
