# THE ANGEL AI Platform Architecture

## Цель

Создать современную AI-платформу, в которой ComfyUI используется исключительно как вычислительный движок.

Пользователь никогда не взаимодействует с нодами напрямую.

---

# Основные слои системы

## Layer 1

Frontend (Electron)

Отвечает за:

* интерфейс
* настройки
* проекты
* управление генерацией

---

## Layer 2

Workflow Adapter Layer

Отвечает за:

* анализ workflow
* преобразование workflow в UI
* связь между интерфейсом и ComfyUI

---

## Layer 3

Comfy Bridge

Отвечает за:

* REST API
* WebSocket
* загрузку workflow
* получение результатов

---

## Layer 4

ComfyUI Engine

Отвечает за:

* выполнение workflow
* управление моделями
* вычисления

---

## Layer 5

Execution Backend

Поддерживаемые режимы:

* Local PC
* Kaggle
* Cloud GPU
* Dedicated Server

---

# Главный принцип

Frontend никогда не зависит напрямую от конкретной модели.

Frontend работает только через Workflow Adapter Layer.

---

# Плагины

Каждая модель подключается как отдельный плагин.

Примеры:

* Flux
* Wan
* LTX
* Hunyuan
* Qwen Image

---

# Долгосрочная цель

Любой новый workflow должен подключаться без изменения ядра приложения.
