# _kaggle_tests — локальные инструменты тестирования (НЕ для GitHub)

Папка в `.gitignore`. Здесь живёт драйвер, которым я гоняю код на реальном
Kaggle Jupyter Server (2× T4) через REST + websocket, и временные тест-скрипты.

## Файлы
- `_kaggle_driver.py` — драйвер: загрузка файлов и выполнение кода в удалённом kernel.
- `.jbase` — base URL Kaggle Jupyter-proxy (**JWT в нём эфемерный**, обновлять на новый сеанс).
- `.jkid` — кеш id текущего kernel'а (создаётся автоматически).
- `.jcode_*.py` — временные фрагменты кода, которые выполнялись на инстансе.

## Запуск (нужен Python с pip + requests + websocket-client)
```bash
PY='/c/Users/githe/AppData/Local/Programs/Python/Python312/python.exe'
"$PY" _kaggle_driver.py upload <remote_path> <local_path>   # загрузить файл
"$PY" _kaggle_driver.py exec <local_code.py> [timeout_sec]  # выполнить код в kernel
"$PY" _kaggle_driver.py newkernel                           # новый kernel
```

Новый сеанс Kaggle → вставь свежий proxy-URL в `.jbase` и удали `.jkid`.
