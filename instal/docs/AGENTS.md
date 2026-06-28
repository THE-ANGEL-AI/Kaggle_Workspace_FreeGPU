# Kaggle ComfyUI Launcher — Правила для агентов

## Архитектура

```
ComfyLauncher (launcher.py)
├── launch() — точка входа (вызывается из ячейки)
│   ├── Thread: _heartbeat_loop    (keep-alive #1: widgets.HTML)
│   ├── Thread: _stdout_keep_alive (keep-alive #2: stdout print)
│   ├── Thread: _startup           (запуск ComfyUI + туннель)
│   └── _keep_alive()              (осн. поток занят — Kaggle не усыпит)
│
├── _startup()
│   ├── _cleanup_old()       — pkill старых, чистка .db
│   ├── _check_git_updates() — git fetch/pull
│   ├── _check_files()       — venv, torch, ноды
│   ├── _ensure_cloudflared()
│   ├── _start_comfy()       — subprocess.Popen(main.py)
│   ├── _wait_for_port()     — socket на 127.0.0.1:8188
│   └── _start_tunnel()      — cloudflared tunnel
│
└── _on_stop() / _on_restart() — callback'и кнопок
```

**LogManager (logging_ui.py)**
- `LogManager.print(text)` — добавляет строку в буфер (thread-safe)
- `_log_flusher` (daemon thread) — раз в 0.5с перерисовывает `widgets.HTML`
- Кнопки — `widgets.Button` с `on_click`
- Панель собирается в `_build_ui()` и показывается через `display()`

---

## ⚠️ Жёсткие правила (нарушение = поломка)

### 1. `_keep_alive()` ОБЯЗАТЕЛЕН в launch()
Если `launch()` завершается — Kaggle видит, что ячейка простаивает >30 мин, и убивает сессию. `_keep_alive()` вызывается синхронно в конце `launch()` и блокирует поток.

**Тело — только sleep + flush. Ничего лишнего:**
```python
def _keep_alive(self):
    while not self.stopped:
        time.sleep(0.1)
        sys.stdout.flush()
```

### 2. НИКОГДА не вызывать `Kernel.do_one_iteration()` из синхронного кода
Это async корутина (IPython 8+). Из `_keep_alive()` не работает — только RuntimeWarning.

**Workflow:** кнопки on_click не работают, пока крутится `_keep_alive()`.
- Нажать ⏹ **Interrupt** в тулбаре Kaggle → `_keep_alive()` получает KeyboardInterrupt, убивает процессы
- Ячейка завершается → kernel свободен → **кнопки работают**

### 3. Лог — ТОЛЬКО `widgets.HTML`, НЕ `widgets.Output`
- ✅ `widgets.HTML.value = html` — работает из любого потока через iopub
- ❌ `widgets.Output + clear_output()` — требует pump (не работает без do_one_iteration)
- ❌ `sys.stdout.write()` — дублирует строки под виджетом
- ❌ `print()` в `LogManager.print()` — дублирует под виджетом

**Куда выводить логи:**
```python
# Только в виджет — НЕ в stdout!
self.logger.print("[*] Сообщение")

# stdout — ТОЛЬКО для anti-sleep маяка (раз в 5 мин)
print("💓 keep-alive", flush=True)
```

### 4. `--use-split-cross-attention` ОБЯЗАТЕЛЕН на T4
Без него дефолтный attention жрёт больше VRAM → OOM-killer → SIGKILL -9.
Это **не ускорение**, а совместимость. Не убирать.

### 5. Другие флаги — НЕ ДОБАВЛЯТЬ
- `--fp16 / --bf16` — не нужны, ComfyUI сам выбирает точность
- `--xformers` — нестабильно на T4 с некоторыми нодами
- `--gpu-only` — CUDA illegal memory access (вытеснение из VRAM)
- `--force-fp16` — может сломать ноды с CPU-операциями

### 6. AIMDO — отключать ЧЕРЕЗ `os.environ`, НЕ `env=` в Popen
```python
# ✅ ПРАВИЛЬНО
os.environ["COMFY_AIMDO_ENABLED"] = "0"

# ❌ НЕПРАВИЛЬНО — ломает процесс (exit code 1, причина неизвестна)
proc = subprocess.Popen([...], env=dict(os.environ, COMFY_AIMDO_ENABLED="0"))
```

`comfy-aimdo` вызывает `hostbuf_file_reader_read failed` → `CUDA illegal memory access` на Kaggle.

---

## Потоки (все daemon=True)

| Поток | Откуда | Что делает |
|---|---|---|
| `_heartbeat_loop` | launch() | heartbeat в widgets.HTML каждые 30с |
| `_stdout_keep_alive` | launch() | пульс в stdout каждые 5 мин |
| `_startup` | launch() | весь pipeline (env, ноды, ComfyUI, туннель) |
| `stream_process` | _start_comfy() | читает stdout ComfyUI в лог |
| `_read_tunnel_output` | _start_tunnel() | читает stdout туннеля, ищет URL |
| `_log_flusher` | LogManager.__init__ | перерисовывает html-лог раз в 0.5с |

---

## История поломок

| Ошибка | Симптом | Фикс |
|---|---|---|
| widgets.Output с clear_output() | лог не обновляется | widgets.HTML.value = html |
| sys.stdout.write() в LogManager.print() | дубли строк под виджетом | убрать sys.stdout.write() |
| удалён _keep_alive() | Kaggle убивает сессию | вернуть sleep+flush |
| ip.kernel.do_one_iteration() | RuntimeWarning: async | убрать pump |
| env={...} в Popen для AIMDO | процесс падает с code 1 | os.environ["COMFY_AIMDO_ENABLED"] = "0" |
| убран --use-split-cross-attention | OOM-killer SIGKILL -9 | вернуть флаг |
| --gpu-only | CUDA illegal memory access | убрать флаг |

---

## Контракт: что проверять перед коммитом

1. **Синтаксис:**
   ```
   python -c "compile(open('instal/launcher.py',encoding='utf-8').read(),'launcher.py','exec')"
   ```
2. **Нет RuntimeWarning/DeprecationWarning** в тестовом прогоне
3. **Логи — только в виджет:** нет sys.stdout.write / print в `LogManager.print()`
4. **Нет pump:** нет `do_one_iteration` в коде
5. **AIMDO отключён:** `os.environ["COMFY_AIMDO_ENABLED"] = "0"` на месте
6. **split-cross-attention:** флаг `--use-split-cross-attention` в `_start_comfy()`
7. **keep-alive:** `self._keep_alive()` — последний вызов в `launch()`
8. **Никаких новых флагов ускорения** без обоснования в этом файле
