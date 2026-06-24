# 🌐 Kaggle Workspace — landing page (GitHub Pages)

Это **ветка `site`** репозитория [THE-ANGEL-AI/Kaggle_Workspace_FreeGPU](https://github.com/THE-ANGEL-AI/Kaggle_Workspace_FreeGPU).
В ней живёт только React-сайт (Vite + React 19 + TypeScript + Framer Motion),
который деплоится на GitHub Pages через GitHub Actions.

**Сам проект (Kaggle-скрипты, ComfyUI workflow, блокноты) лежит в ветке [`main`](https://github.com/THE-ANGEL-AI/Kaggle_Workspace_FreeGPU/tree/main).**

| Ссылка | Назначение |
| --- | --- |
| 🐙 [GitHub репозиторий (main)](https://github.com/THE-ANGEL-AI/Kaggle_Workspace_FreeGPU) | Kaggle-скрипты и workflow |
| 🌐 [GitHub Pages](https://the-angel-ai.github.io/Kaggle_Workspace_FreeGPU/) | Лендинг (этот сайт) |
| 📓 Блокноты | `main` → `Notebook/` |
| 🎨 Workflow | `main` → `workflows/` |

## 🛠️ Локальная разработка

```bash
npm install
npm run dev          # dev-сервер на http://localhost:5173
npm run typecheck    # tsc --noEmit
npm run build        # собирает в docs-site/dist (для GH Pages)
```

Базовый URL зашит в `vite.config.ts` как `/Kaggle_Workspace_FreeGPU/`,
поэтому локальные ассеты корректно собираются и под production GH Pages subpath.

## 🚀 Деплой

Workflow (`.github/workflows/pages.yml`) триггерится на каждый push в `site`:
1. `npm ci` — установка зависимостей (`package-lock.json` обязателен).
2. `npm run build` — Vite собирает в `docs-site/dist`.
3. `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4`
   публикуют артефакт в окружение GitHub Pages.

> Правки в `main` (`instal/`, `workflows/`, `Notebook/`) CI-воркфлоу не
> запускают — это и есть основная выгода разделения.
