# ☁️ Kaggle Cloud — ComfyUI на бесплатных 2× Tesla T4

> Проект **[THE ANGEL AI](https://vk.com/theangel_lab)** — запускаем тяжёлые
> генеративные пайплайны **ComfyUI** (Flux2 GGUF, LTX 2.3 Video, TTS) прямо в
> бесплатном Kaggle-блокноте на **двух Tesla T4**, без локального GPU и без
> оплаты облака.

[![Поддержать проект](https://img.shields.io/badge/💖_Поддержать-Boosty-f15f2c?style=for-the-badge)](https://boosty.to/the_angel/donate)
[![ВКонтакте](https://img.shields.io/badge/Сообщество-ВКонтакте-0077FF?style=for-the-badge&logo=vk)](https://vk.com/theangel_lab)

---

## 🎯 Что это и зачем

Kaggle бесплатно даёт **2× Tesla T4 (по 16 ГБ) на 30 часов в неделю** — этого
хватает, чтобы крутить Flux2, видео-пайплайны и TTS. Но «голый» Kaggle — это боль:

- ❌ окружение слетает после каждого рестарта сессии
- ❌ бинарники теряют бит исполнения (`+x`) — файлы есть, но не работают
- ❌ при обновлении ядра Kaggle старый Python несовместим с новой libc
- ❌ мульти-GPU (2× T4) конфликтует без правильной настройки
- ❌ через 40 минут бездействия Kaggle усыпляет сессию

**Этот репозиторий превращает запуск в одну строку и чинит всё автоматически.**

---

## 📂 Структура

```
Kaggle_Workspace_FreeGPU/
├─ README.md                  # этот файл
├─ instal/                    # ☕ ядро: скрипты установки и запуска
│  ├─ instal_comfyui.py       #   ШАГ 1: uv + venv + torch cu130 + ComfyUI
│  ├─ instal_castom_node.py   #   ШАГ 2: кастомные ноды + модели
│  ├─ start.py                #   ШАГ 3: запуск + туннель + панель + keep-alive
│  └─ kaggle_env.py           #   движок: пути, uv, ремонт venv, диагностика
├─ Notebook/                  # 📓 готовые блокноты для импорта в Kaggle
│  ├─ confyui-main.ipynb
│  └─ gemma_kaggle_server.ipynb
├─ workflows/                 # 🎨 ComfyUI-воркфлоу (импорт drag-n-drop)
│  ├─ Flux2dev32b_GGUF.json
│  ├─ Flux2dev32b_GGUF v2 API.json
│  └─ LTX_Director-V2-Beta.json
├─ docs-site/                 # 🌐 сайт документации (GitHub Pages)
└─ _kaggle_tests/             # 🧪 тесты для проверки на Kaggle
```

---

## 🚀 Быстрый старт

Открой блокнот Kaggle, включи **GPU T4 ×2** и интернет, выполни по порядку:

```python
# 0. Получить скрипты (первый раз — clone, потом — pull)
!git clone https://github.com/THE-ANGEL-AI/Kaggle_Workspace_FreeGPU.git || \
 git -C Kaggle_Workspace_FreeGPU pull

# 1. ComfyUI + Manager
!python Kaggle_Workspace_FreeGPU/instal/instal_comfyui.py

# 2. Кастомные ноды + модели
!python Kaggle_Workspace_FreeGPU/instal/instal_castom_node.py

# 3. Запуск + Cloudflare-туннель + панель управления
%run Kaggle_Workspace_FreeGPU/instal/start.py
```

> 💡 **Можно одной строкой.** `start.py` сам проверит окружение, доставит
> недостающее и запустит всё. Для холодного старта достаточно `%run .../instal/start.py`.

После шага 3 под ячейкой появятся кнопки:

| Кнопка | Что делает |
|--------|-----------|
| 🔗 **Открыть ComfyUI** | Публичная ссылка Cloudflare (новая на каждый запуск) |
| 🛑 **Остановить** | Гасит ComfyUI и туннель без перезапуска ядра |
| 🔄 **Перезапустить** | Поднимает ComfyUI заново (новый URL) |

---

## 🏗️ Архитектура: три шага

| Шаг | Файл | Что ставит / делает | Запуск |
|-----|------|---------------------|--------|
| 1 | `instal_comfyui.py` | uv + venv (Python 3.12) + torch cu130 + ComfyUI + Manager + общие пакеты | `!python instal/instal_comfyui.py` |
| 2 | `instal_castom_node.py` | 8 кастомных нод из списка + симлинки моделей из `/kaggle/input` + авто-инжекция SageAttention-T4 в workflow | `!python instal/instal_castom_node.py` |
| 3 | `start.py` | проверка/ремонт окружения → сборка SageAttention-SM75 + symlink ноды → ComfyUI → Cloudflare-туннель → панель кнопок → keep-alive | `%run instal/start.py` |
| — | `kaggle_env.py` | **ядро системы**: пути, uv, создание/ремонт/диагностика venv, `install_python()` | импортируется всеми |

---

## 🛡️ Самоисцеление: как окружение чинится само

**Проблема.** Kaggle при рестарте сессии:
1. 🧨 **Сбрасывает бит `+x`** — файлы на месте, но не исполняются
2. 🧨 **Обновляет ядро ОС** — старый CPython (скомпилирован под другую libc)
   падает при запуске. Файл есть, а запустить нельзя.

**Как это чинится (3 уровня, по возрастанию стоимости):**

```
venv сломан?
 ├─ 🔧 Уровень 1 — восстановить +x (секунда)
 │   Если venv/bin/python и базовый CPython просто потеряли бит исполнения —
 │   chmod 755 чинит всё за миллисекунды. Torch не трогаем.
 │
 ├─ 🔧 Уровень 2 — переустановить базовый CPython (10-30 сек)
 │   Если +x не помог — значит, обновилось ядро Kaggle. Старый CPython
 │   несовместим с новой libc → удаляем его и ставим свежий через uv.
 │   Пакеты в venv пока живы (но симлинк битый, venv всё равно не работает).
 │
 └─ 🔧 Уровень 3 — пересоздать venv + torch (из кэша — быстро)
     Старый venv удаляется, создаётся новый на свежем CPython.
     Torch и пакеты переставляются из uv-кэша — не качаются заново.
     После этого start.py автоматически переустанавливает зависимости нод.
```

<details>
<summary><b>🔬 Технически: как это работает</b></summary>

```python
def install_python():
    """Единая точка входа: uv + venv (создан/починен/пересоздан)
       Returns: True если всё уже работало, False если был ремонт
    """
    ensure_uv()
    return ensure_venv()

def venv_python_ok():
    """Проверка реальным запуском, а не os.path.exists"""
    subprocess.run([VENV_PYTHON, "-c", "pass"],
                   check=True, capture_output=True, timeout=30)

def repair_venv_perms():
    """Уровень 1: быстро чинит +x на всём исполняемом"""
    candidates = [venv/bin/python, реальный CPython, uv, python3*]
    for c in candidates: os.chmod(c, 0o755)

def repair_base_python_via_uv():
    """Уровень 2: CPython несовместим с ядром — переустановка"""
    shutil.rmtree(UV_PYTHON_DIR)
    run(["uv", "python", "install", "3.12"])

def ensure_venv():
    """Уровень 3: uv venv --clear (пакеты из кэша), возвращает флаг"""
    if venv_python_ok(): return True   # всё ок
    if repair_venv_perms(): return False  # +x починил
    repair_base_python_via_uv()
    run(["uv", "venv", ... "--clear"])
    return False  # был пересоздан — torch мог пропасть
```
</details>

### 🩺 Диагностика: почему сломалось

Если venv не работает — скрипт **точно скажет причину** в логе:

| Симптом | Диагноз | Что сделает скрипт |
|---------|---------|-------------------|
| `No such file or directory` | Битый симлинк — `venv/bin/python` ведёт в никуда | Пересоздаст venv |
| `Permission denied` | Слетел бит `+x` | chmod 755 (секунда) |
| `version GLIBC_2.38 not found` | Обновилось ядро Kaggle, старый CPython несовместим | `uv python install` (свежий CPython) |
| `FATAL: kernel too old` | Ядро ОС новее, чем тот, под которое собран CPython | То же — переустановка CPython |

---

## 🔒 Защита от усыпания Kaggle

**Проблема.** Kaggle через ~40 минут бездействия показывает *"Are you still there?"*
и может остановить сессию, особенно если вкладка свёрнута.

**Как мы это решили:**

```
2 независимых слоя keep-alive, работающих параллельно:

┌─────────────────────────────────────────────────────┐
│ 🖥️  Слой 1: Heartbeat-виджет (каждые 30 сек)        │
│    Обновляет HTML-строку в панели управления.         │
│    Создаёт трафик ядро → браузер — Kaggle видит       │
│    активность и не трогает сессию.                    │
│    Живёт, пока открыта вкладка.                       │
├─────────────────────────────────────────────────────┤
│ 📢  Слой 2: Stdout-пульс (каждые 5 минут)            │
│    Пишет 💓 [14:32:01] ComfyUI активен... прямо       │
│    в stdout ячейки через print(flush=True).           │
│    Гарантированно отправляет данные на сервер Kaggle  │
│    даже если вкладка свёрнута — не зависит от         │
│    браузера. Предотвращает "Are you still there?".    │
└─────────────────────────────────────────────────────┘
```

<details>
<summary><b>🔬 Технически: два потока в start.py</b></summary>

```python
def launch(self):
    Thread(target=self._heartbeat_loop, daemon=True).start()    # виджет, 30с
    Thread(target=self._stdout_keep_alive, daemon=True).start() # stdout, 5 мин
    Thread(target=self._startup, daemon=True).start()
    self._keep_alive()  # основной цикл ячейки (держит kernel активным)

def _stdout_keep_alive(self):
    print("🔒 [ЗАЩИТА] Система защиты Kaggle активирована!", flush=True)
    while not self.stopped:
        time.sleep(300)
        now = datetime.now().strftime("%H:%M:%S")
        print(f"💓 [{now}] ComfyUI активен, ожидание запроса...", flush=True)
```
</details>

---

## ⚡ Что оптимизировано для скорости на T4

| Оптимизация | Зачем |
|-------------|-------|
| **uv вместо pip** | Параллельная установка пакетов, torch в разы быстрее |
| **torch cu130** | CUDA 13.0 — драйвер Kaggle 580.x его держит; на cu128 был warning и медленный путь |
| **SageAttention-SM75** 🆕 | **Собственный CUDA-кернел** под T4 (Turing): INT8 QK + FP16 PV + FP32 accum. До **2.5×** attention на длинных контекстах. Работает как ComfyUI custom node (`SageAttention-T4 Apply`) — через `add_object_patch()`, без глобальных monkey-patch и без флагов запуска |
| **Без xformers** | Несовместим с T4 (sm_75). Раньше fallback на `--use-pytorch-cross-attention`, теперь на `--use-split-cross-attention` |
| **ComfyUI-MultiGPU** | DisTorch2 вместо старого хака ComfyBootlegOffload (они конфликтовали) |
| **Без tensorflow / старых пинов** | Тянут свои версии CUDA, ломают современные ноды |
| **smart-memory включён** | Модель кэшируется в VRAM между генерациями |
| **uv-кэш в /kaggle/working** | Wheels (torch и др.) переживают рестарт — переустановка из кэша, не из сети |

---

## 🧠 SageAttention-SM75 — ускоренное внимание на T4

> **Собственный CUDA-кернел** под архитектуру Turing (sm_75) — INT8 тензорные ядра
> для QK⊤ + FP16 для PV + FP32 аккумуляция. Работает на T4, RTX 2080, Quadro RTX.

Кернел живёт в форке **[THE-ANGEL-AI/SageAttention-SM75-path](https://github.com/THE-ANGEL-AI/SageAttention-SM75-path)**. `start.py` при старте:
1. Клонирует/обновляет форк
2. Собирает CUDA-расширение через `pip install -e .`
3. Создаёт **symlink** в `custom_nodes/SageAttention-T4` — ComfyUI видит ноду
4. **Авто-инжектит** ноду `SageAttention-T4 Apply` в сохранённые workflow

Всё это происходит **автоматически** при каждом запуске. Если сборка не удалась — fallback на `--use-split-cross-attention`.

### 📊 Прирост скорости

| Длина контекста | Ускорение attention | End-to-end (видео) |
|----------------|--------------------|--------------------|
| 2K | ~1.3× | +10-15% |
| 8K | ~1.8× | +30-40% |
| 16K | ~2.5× | +60-75% |

### 🔌 ComfyUI Custom Node

После установки в меню нод появляется категория **🧠 SageAttention-T4** с двумя нодами:

| Нода | Назначение |
|------|-----------|
| **SageAttention-T4 Apply** | Вставь между загрузчиком модели и сэмплером. Параметры: `smooth_k` (on/off), `enable` (on/off) |
| **SageAttention-T4 Remove** | Убирает патч, возвращает оригинальное внимание |

Нода использует `model.add_object_patch()` — патч действует **только на эту модель**, не ломая другие части workflow. Workflow-файлы в `ComfyUI/user/default/workflows/` автоматически получают ноду при запуске.

---

## 🖥️ Мульти-GPU (2× T4)

В графе используй ноды **ComfyUI-MultiGPU** (DisTorch2):
- `UnetLoaderGGUFAdvancedDisTorch2MultiGPU` — для Flux2-GGUF
- `*CLIPLoaderGGUFDisTorch2MultiGPU` — для текст-энкодера

Они распределяют слои между `cuda:0`, `cuda:1` и CPU. Для двух T4 удобно начать
с режима Virtual VRAM или ratio (0.6 / 0.4 между картами).

---

## 📦 Модели

Симлинки из `/kaggle/input` → папки ComfyUI. Настраиваются в `instal_castom_node.py` (список `SYMLINKS`).

### Flux2 Dev (GGUF)

| Файл | Назначение |
|------|-----------|
| `flux2-dev-Q4_0.gguf` | Основная модель (диффузия) |
| `mistral_3_small_flux2_fp8.safetensors` | Текст-энкодер (CLIP) |
| `flux2-vae.safetensors` | VAE |

### LTX 2.3 Video

| Файл | Назначение |
|------|-----------|
| `ltx-2.3-22b-distilled-1.1-Q6_K.gguf` | Основная модель |
| `gemma-3-12b-it-heretic-fp4-comfy.safetensors` | Текст-энкодер |
| `ltx-2.3_text_projection_bf16.safetensors` | Текст-проекция |
| `LTX23_video_vae_bf16.safetensors` | Видео-VAE |
| `LTX23_audio_vae_bf16.safetensors` | Аудио-VAE |
| `taeltx2_3.safetensors` | VAE |
| `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` | Апскейлер |
| `LTX-2.3-22b-AV-LoRA-talking-head-v1.safetensors` | LoRA (говорящая голова) |
| `LTX-2.3-OmniNFT-RL-Lora_bf16.safetensors` | LoRA |
| `ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors` | LoRA |

---

## 🧩 Кастомные ноды

Ставятся автоматически на шаге 2. Список — словарь `CUSTOM_NODES` в `instal_castom_node.py`.

| Нода | Назначение |
|------|-----------|
| **ComfyUI-Crystools** | Мониторинг GPU, температуры, VRAM |
| **ComfyUI-GGUF** | Загрузка GGUF-моделей (Flux2, LTX) |
| **ComfyUI-Logic** | Логические операторы в графе |
| **comfy-image-saver** | Сохранение изображений с метаданными |
| **ComfyUI-MultiGPU** | Multi-GPU (DisTorch2) для 2× T4 |
| **ComfyUI-KJNodes** | Утилиты: маски, латенты, пайплайны |
| **ComfyUI_FL-CosyVoice3** | TTS — синтез и клонирование речи |
| **WhatDreamsCost-ComfyUI** | LTX 2.3 Director (таймлайн-оркестратор видео) |
| **SageAttention-T4** 🆕 | Кастомная нода — INT8-внимание через `add_object_patch()`. Ставится `start.py` из [THE-ANGEL-AI/SageAttention-SM75-path](https://github.com/THE-ANGEL-AI/SageAttention-SM75-path) |
| **ComfyUI-Manager** | Менеджер нод (ставится на шаге 1) |

---

## 🔧 Настройка под себя

| Что хочешь сделать | Куда идти |
|--------------------|-----------|
| ➕ Добавить ноду | `CUSTOM_NODES` в `instal_castom_node.py` |
| ➕ Добавить модель | `SYMLINKS` в `instal_castom_node.py` |
| 📦 Общий pip-пакет | `install_common_extras()` в `instal_comfyui.py` |
| 🧠 SageAttention (сборка/нода) | `_install_sage_attention()` в `start.py` — меняй URL форка или флаги компиляции |
| 🚀 Флаги запуска ComfyUI | `_start_comfy()` в `start.py` |
| 🔄 Частоту пульса keep-alive | `_stdout_keep_alive()` в `start.py` (сейчас 300 сек) |

> 🔄 **Авто-обновление.** `start.py` при старте делает `git pull --ff-only` —
> правки скриптов прилетают на Kaggle сами.

---

## 🌐 Лендинг / GitHub Pages

React-сайт проекта (Vite + React 19 + TypeScript + Framer Motion) живёт
в **ветке [`site`](https://github.com/THE-ANGEL-AI/Kaggle_Workspace_FreeGPU/tree/site)**
этого репозитория. Ветка `main` содержит только скрипты — без тяжёлого кода сайта.
Задеплоено через GitHub Actions.

---

## 💖 Поддержать проект

Проект развивается силами **THE ANGEL AI** и остаётся бесплатным. Если он
сэкономил вам деньги на облаке или GPU — поддержите развитие:

### 👉 **[Поддержать на Boosty](https://boosty.to/the_angel/donate)**

## 🌐 Сообщество

Вопросы, гайды, анонсы и помощь по запуску — в нашей группе:

### 👉 **[THE ANGEL AI — ВКонтакте](https://vk.com/theangel_lab)**

---

<p align="center"><b>THE ANGEL AI</b> · сделано с ❤️ для тех, у кого нет своего GPU</p>
