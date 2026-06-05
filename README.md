# ComfyUI Flux2 на Kaggle (2× T4)

Блокнот `comfyui-flux2.ipynb` сведён к **трём строкам запуска**. Вся логика — в трёх Python-скриптах.

## Структура

| Файл | Что делает |
|------|-----------|
| `instal_comfyui.py` | Ставит ComfyUI + ComfyUI-Manager через **uv** (быстрее virtualenv). torch под **CUDA 13.0**, Python **3.12**. |
| `instal_castom_node.py` | Ставит кастомные ноды (Crystools, GGUF, Logic, image-saver, QwenVL, **ComfyUI-MultiGPU/DisTorch2**) и делает symlink на модели. |
| `start.py` | Запускает ComfyUI + Cloudflare-туннель. Под ячейкой — кнопки **«Открыть ComfyUI»**, **«Остановить ComfyUI»**, **«Перезапустить»** + живой лог. |

## Запуск

Положи 3 `.py` рядом с блокнотом в `/kaggle/working`, затем выполни ячейки:

```python
!python instal_comfyui.py
!python instal_castom_node.py
%run start.py
```

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

- Список нод — `CUSTOM_NODES` в `instal_castom_node.py`.
- Ссылки на модели — `SYMLINKS` в `instal_castom_node.py`.
- Версия Python / канал torch — константы вверху `instal_comfyui.py`.

## Мульти-GPU (2× T4)

В рабочем процессе используй ноды **ComfyUI-MultiGPU** (DisTorch2):
`UnetLoaderGGUFAdvancedDisTorch2MultiGPU` для Flux2-GGUF и
`*CLIPLoaderGGUFDisTorch2MultiGPU` для текст-энкодера — они распределяют
слои между `cuda:0`, `cuda:1` и CPU. Для двух T4 удобно начать с режима
Virtual VRAM или ratio (например, 0.6/0.4 между картами).
