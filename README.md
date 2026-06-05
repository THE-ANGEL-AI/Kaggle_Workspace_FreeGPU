# ComfyUI Flux2 на Kaggle (2× T4)

Блокнот `comfyui-flux2.ipynb` сведён к **трём строкам запуска**. Вся логика — в трёх Python-скриптах.

## Структура

| Файл | Что делает |
|------|-----------|
| `instal_comfyui.py` | Ставит ComfyUI + ComfyUI-Manager через **uv** (быстрее virtualenv). torch под **CUDA 12.8**, Python **3.12**. |
| `instal_castom_node.py` | Ставит кастомные ноды (Crystools, GGUF, Logic, image-saver, QwenVL, **ComfyUI-MultiGPU/DisTorch2**) и делает symlink на модели. |
| `start.py` | Запускает ComfyUI + Cloudflare-туннель. Под ячейкой — кнопки **«Открыть ComfyUI»** и **«Остановить ComfyUI»** + живой лог. |

## Запуск

Положи 3 `.py` рядом с блокнотом в `/kaggle/working`, затем выполни ячейки:

```python
!python instal_comfyui.py
!python instal_castom_node.py
%run start.py
```

## Что оптимизировано для скорости на T4

- **uv вместо virtualenv** — установка зависимостей в разы быстрее.
- **torch cu128 (стабильный)** под драйвер Kaggle и карты T4.
- **Без xformers** — последние сборки не содержат ядер для Turing (T4) и
  только тормозят. Вместо них нативный **PyTorch SDPA**
  (`--use-pytorch-cross-attention`) — быстрое внимание на T4.
- **ComfyUI-MultiGPU (DisTorch2)** вместо хака `ComfyBootlegOffload.py`.
  Старый гист и DisTorch2 оба патчат выгрузку слоёв и конфликтовали —
  отсюда долгая генерация на двух T4. Оставлена только официальная нода.
- **Без tensorflow и старых пинов** `diffusers==0.27.0`/`transformers==4.37.2` —
  они тянули свои CUDA/численные библиотеки и ломали современные ноды.
- **smart-memory включён** — модель кэшируется в VRAM между генерациями.

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
