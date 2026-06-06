# ComfyUI Flux2 на Kaggle (2× T4)

Блокнот `comfyui-flux2.ipynb` сведён к **трём строкам запуска**. Вся логика — в трёх Python-скриптах внутри папки `instal/`.

## Структура

```
Kaggle_Cloud/
├─ comfyui-flux2.ipynb     # блокнот в 3 строки запуска
├─ instal/                 # все установочные скрипты (папка расширяется)
│  ├─ instal_comfyui.py
│  ├─ instal_castom_node.py
│  └─ start.py
└─ README.md
```

| Файл | Что делает |
|------|-----------|
| `instal/instal_comfyui.py` | Ставит ComfyUI + ComfyUI-Manager через **uv** (быстрее virtualenv). torch под **CUDA 13.0**, Python **3.12**. |
| `instal/instal_castom_node.py` | Ставит кастомные ноды (Crystools, GGUF, Logic, image-saver, QwenVL, **ComfyUI-MultiGPU/DisTorch2**) и делает symlink на модели. |
| `instal/start.py` | Запускает ComfyUI + Cloudflare-туннель. Под ячейкой — кнопки **«Открыть ComfyUI»**, **«Остановить ComfyUI»**, **«Перезапустить»** + живой лог. |

## Запуск

Положи папку `instal/` рядом с блокнотом в `/kaggle/working`, затем выполни ячейки:

```python
!python instal/instal_comfyui.py
!python instal/instal_castom_node.py
%run instal/start.py
```

## Проверки и идемпотентность

Скрипты можно безопасно перезапускать — каждый шаг сначала проверяет, не сделан ли он:

- **`instal_comfyui.py`** — ставит `uv` только если его нет (`shutil.which`), при ошибке
  PEP 668 (`externally-managed-environment`) повторяет с `--break-system-packages`;
  не пересоздаёт рабочий venv; не переустанавливает torch, если CUDA уже видна;
  пропускает `apt` если `ffmpeg` уже стоит.
- **`instal_castom_node.py`** — перед работой проверяет, что ШАГ 1 выполнен (есть `uv`,
  рабочий venv, папка `custom_nodes`), иначе выходит с подсказкой.
- **`start.py`** — проверяет venv **запуском** (а не наличием файла). Если venv пропал
  или стал нерабочим (битый симлинк после рестарта сессии Kaggle) — **автоматически
  перезапускает `instal_comfyui.py`**, пересоздаёт venv и переустанавливает torch.

### Почему venv «теряется» (важно)

Папка `/kaggle/working/venv` переживает рестарт сессии, но управляемый `uv`-ом
CPython, на который ссылается `venv/bin/python`, лежит в кэше (`~/.cache`) и **не**
переживает. Симлинк становится битым → ComfyUI не стартует. Поэтому `start.py`
проверяет venv реальным запуском и при поломке чинит его сам.

## Что оптимизировано для скорости на T4

- **uv вместо virtualenv** — установка зависимостей в разы быстрее.
- **torch cu130 (CUDA 13.0)** — драйвер Kaggle (580.x) его поддерживает, и
  ComfyUI 0.24 включает на нём оптимизированные CUDA-операции. На cu128 был
  warning `You need pytorch with cu130 or higher` и более медленный путь.
  Откат: поменяй `TORCH_INDEX` на `.../whl/cu128` в `instal_comfyui.py`.
- **Без xformers** — последние сборки не содержат ядер для Turing (T4) и
  только тормозят. Вместо них нативный **PyTorch SDPA**
  (`--use-pytorch-cross-attention`) — быстрое внимание на T4.
- **ComfyUI-MultiGPU (DisTorch2)** вместо хака `ComfyBootlegOffload.py`.
  Старый гист и DisTorch2 оба патчат выгрузку слоёв и конфликтовали —
  отсюда долгая генерация на двух T4. Оставлена только официальная нода.
- **Без tensorflow и старых пинов** `diffusers==0.27.0`/`transformers==4.37.2` —
  они тянули свои CUDA/численные библиотеки и ломали современные ноды.
- **smart-memory включён** — модель кэшируется в VRAM между генерациями.

## Кнопки управления (под ячейкой `start.py`)

- **🔗 Открыть ComfyUI** — публичная ссылка Cloudflare (новая на каждый запуск).
- **🛑 Остановить ComfyUI** — гасит процесс и туннель, освобождает порт
  **без перезапуска ядра Kaggle**.
- **🔄 Перезапустить** — гасит и поднимает ComfyUI заново (новый URL),
  переустановка не нужна. Удобно подхватить только что добавленную модель/ноду.

## Где править под себя

- Список нод — `CUSTOM_NODES` в `instal/instal_castom_node.py`.
- Ссылки на модели — `SYMLINKS` в `instal/instal_castom_node.py`.
- Версия Python / канал torch — константы вверху `instal/instal_comfyui.py`
  (откат на CUDA 12.8: поменяй `TORCH_INDEX` на `.../whl/cu128`).

## Мульти-GPU (2× T4)

В рабочем процессе используй ноды **ComfyUI-MultiGPU** (DisTorch2):
`UnetLoaderGGUFAdvancedDisTorch2MultiGPU` для Flux2-GGUF и
`*CLIPLoaderGGUFDisTorch2MultiGPU` для текст-энкодера — они распределяют
слои между `cuda:0`, `cuda:1` и CPU. Для двух T4 удобно начать с режима
Virtual VRAM или ratio (например, 0.6/0.4 между картами).
