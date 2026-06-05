#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start.py
=================================================================
ШАГ 3 из 3. Запускает ComfyUI + Cloudflare-туннель и рисует под
ячейкой панель управления.

Что исправлено по сравнению с блокнотом:
  * Ячейка НЕ висит в фоне. Весь запуск идёт в фоновом потоке, а
    ячейка завершается сразу — kernel остаётся свободным.
  * Под ячейкой появляются ДВЕ кнопки:
        — «🔗 Открыть ComfyUI»  (публичная ссылка Cloudflare)
        — «🛑 Остановить ComfyUI» (гасит процесс БЕЗ перезапуска
          ядра Kaggle — раньше это было невозможно)
  * Под кнопками — живой лог ComfyUI и туннеля.
  * Кнопка «Остановить» работает и после завершения ячейки —
    обработчик живёт в ядре, пока открыт блокнот.

Скорость на T4:
  * Запуск с --use-pytorch-cross-attention — нативный PyTorch SDPA
    (быстрое внимание на Turing, заменяет нерабочий на T4 xformers).
  * smart-memory НЕ отключаем — модель кэшируется в VRAM между
    генерациями, повторный прогон быстрее.

Запуск (в блокноте):  %run start.py
=================================================================
"""

import os
import re
import socket
import subprocess
import time
from threading import Thread

import ipywidgets as widgets
from IPython.display import display

# ----------------------------------------------------------------------
# Пути и параметры
# ----------------------------------------------------------------------
HOME_DIR    = "/kaggle/working"
COMFY_DIR   = f"{HOME_DIR}/ComfyUI"
VENV_PYTHON = f"{HOME_DIR}/venv/bin/python"
CLOUDFLARED = f"{HOME_DIR}/cloudflared"
PORT        = 8188
STARTUP_TIMEOUT = 240   # сек на запуск ComfyUI
URL_TIMEOUT     = 90    # сек на получение ссылки Cloudflare


class ComfyLauncher:
    """Держит процессы, виджеты и весь жизненный цикл запуска/остановки."""

    def __init__(self):
        self.comfy_proc = None
        self.tunnel_proc = None
        self.public_url = None
        self.stopped = False
        self._build_ui()

    # ------------------------------------------------------------------
    # UI: статус, кнопки, лог
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.status = widgets.HTML(self._status_html("⏳ Запуск...", "#f39c12"))

        # Кнопка-ссылка появится, когда туннель отдаст URL.
        self.url_box = widgets.HTML(
            "<i style='color:#888'>Публичная ссылка появится здесь...</i>"
        )

        self.stop_btn = widgets.Button(
            description="Остановить ComfyUI",
            icon="stop",
            button_style="danger",
            layout=widgets.Layout(width="220px", height="42px"),
        )
        self.stop_btn.on_click(self._on_stop_click)

        self.log = widgets.Output(layout=widgets.Layout(
            border="1px solid #ddd", height="360px",
            overflow="auto", padding="6px",
            background_color="#0f1117",
        ))

        buttons = widgets.HBox([self.url_box, self.stop_btn])
        self.panel = widgets.VBox([
            self.status,
            buttons,
            widgets.HTML("<b>Лог:</b>"),
            self.log,
        ])

    @staticmethod
    def _status_html(text, color):
        return f"<h3 style='color:{color}; margin:6px 0'>{text}</h3>"

    def _set_status(self, text, color):
        self.status.value = self._status_html(text, color)

    def _print(self, text):
        """Печать в лог-виджет (безопасно из фонового потока)."""
        self.log.append_stdout(text if text.endswith("\n") else text + "\n")

    # ------------------------------------------------------------------
    # Публичная точка входа
    # ------------------------------------------------------------------
    def launch(self):
        display(self.panel)                      # панель появляется под ячейкой
        Thread(target=self._startup, daemon=True).start()  # запуск в фоне
        return self.panel                         # ячейка сразу завершается

    # ------------------------------------------------------------------
    # Поток логов процесса -> лог-виджет
    # ------------------------------------------------------------------
    def _stream(self, proc, prefix):
        for line in iter(proc.stdout.readline, ""):
            if line:
                self._print(f"{prefix}{line.rstrip()}")
            if proc.poll() is not None and not line:
                break

    # ------------------------------------------------------------------
    # Главная последовательность запуска (в фоновом потоке)
    # ------------------------------------------------------------------
    def _startup(self):
        try:
            self._cleanup_old()
            self._check_files()
            self._ensure_cloudflared()
            self._start_comfy()
            self._wait_for_port()
            self._start_tunnel()
        except Exception as e:
            self._set_status(f"❌ Ошибка запуска: {e}", "#e74c3c")
            self._print(f"[ERROR] {e}")

    # --- 1. убиваем старые процессы и чистим блокировки ----------------
    def _cleanup_old(self):
        self._print("[*] Очистка старых процессов...")
        for pat in ("main.py", "comfyui", "cloudflared"):
            subprocess.run(["pkill", "-9", "-f", pat], capture_output=True)
        time.sleep(2)
        for f in (f"{COMFY_DIR}/user/comfyui.db",
                  f"{COMFY_DIR}/user/comfyui.db-journal"):
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass

    # --- 2. проверки файлов -------------------------------------------
    def _check_files(self):
        for path, msg in (
            (COMFY_DIR, "ComfyUI не найден — запусти instal_comfyui.py"),
            (f"{COMFY_DIR}/main.py", "main.py не найден"),
            (VENV_PYTHON, "venv не найден — запусти instal_comfyui.py"),
        ):
            if not os.path.exists(path):
                raise RuntimeError(msg)
        self._print("[*] Файлы ComfyUI на месте")

    # --- 3. cloudflared ------------------------------------------------
    def _ensure_cloudflared(self):
        if not os.path.exists(CLOUDFLARED):
            self._print("[*] Скачиваю cloudflared...")
            subprocess.run([
                "wget", "-q",
                "https://github.com/cloudflare/cloudflared/releases/latest/"
                "download/cloudflared-linux-amd64",
                "-O", CLOUDFLARED,
            ], check=True)
            subprocess.run(["chmod", "+x", CLOUDFLARED], check=True)

    # --- 4. запуск ComfyUI --------------------------------------------
    def _start_comfy(self):
        self._set_status("⏳ Запуск ComfyUI...", "#f39c12")
        self.comfy_proc = subprocess.Popen(
            [
                VENV_PYTHON, "main.py",
                "--listen", "0.0.0.0",
                "--port", str(PORT),
                "--enable-cors-header", "*",
                "--disable-auto-launch",
                "--use-pytorch-cross-attention",  # быстрое внимание на T4 (SDPA)
                "--preview-method", "auto",
            ],
            cwd=COMFY_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        Thread(target=self._stream, args=(self.comfy_proc, "[COMFY] "),
               daemon=True).start()

    # --- 5. ждём порт --------------------------------------------------
    def _wait_for_port(self):
        self._print("[*] Ожидание запуска сервера...")
        start = time.time()
        while True:
            if self.comfy_proc.poll() is not None:
                raise RuntimeError(
                    f"ComfyUI завершился с кодом {self.comfy_proc.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=2):
                    break
            except OSError:
                pass
            if time.time() - start > STARTUP_TIMEOUT:
                raise RuntimeError(f"Таймаут запуска ComfyUI ({STARTUP_TIMEOUT}с)")
            time.sleep(2)
        self._set_status("✅ ComfyUI запущен, поднимаю туннель...", "#27ae60")

    # --- 6. туннель Cloudflare + парсинг URL ---------------------------
    def _start_tunnel(self):
        self.tunnel_proc = subprocess.Popen(
            [
                CLOUDFLARED, "tunnel", "--no-autoupdate",
                "--protocol", "http2",
                "--url", f"http://127.0.0.1:{PORT}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        start = time.time()
        while time.time() - start < URL_TIMEOUT:
            if self.tunnel_proc.poll() is not None:
                raise RuntimeError("Процесс туннеля завершился")
            line = self.tunnel_proc.stdout.readline()
            if not line:
                continue
            self._print(f"[TUNNEL] {line.rstrip()}")
            m = re.search(r"https://[^\s]+trycloudflare\.com", line)
            if m:
                self.public_url = m.group(0)
                break

        # остаток логов туннеля — в фон
        Thread(target=self._stream, args=(self.tunnel_proc, "[TUNNEL] "),
               daemon=True).start()

        if self.public_url:
            self._show_url(self.public_url)
            self._set_status("✅ ComfyUI доступен!", "#27ae60")
        else:
            self._set_status("⚠️ Туннель поднят, но ссылку найти не удалось — "
                             "проверь лог", "#f39c12")

    # ------------------------------------------------------------------
    # Кнопка-ссылка
    # ------------------------------------------------------------------
    def _show_url(self, url):
        self.url_box.value = (
            f"<a href='{url}' target='_blank' rel='noopener noreferrer' "
            f"style='background:#3498db; color:white; padding:10px 22px; "
            f"text-decoration:none; border-radius:8px; font-size:15px; "
            f"font-weight:bold; display:inline-block; margin-right:12px;'>"
            f"🔗 Открыть ComfyUI</a>"
            f"<div style='font-size:11px; color:#888; margin-top:6px'>{url}</div>"
        )

    # ------------------------------------------------------------------
    # Кнопка «Остановить»
    # ------------------------------------------------------------------
    def _on_stop_click(self, _btn):
        if self.stopped:
            return
        self.stopped = True
        self._set_status("⏳ Останавливаю ComfyUI...", "#f39c12")
        self.stop_btn.disabled = True

        for proc in (self.tunnel_proc, self.comfy_proc):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
        # подчищаем хвосты на всякий случай
        for pat in ("main.py", "cloudflared"):
            subprocess.run(["pkill", "-9", "-f", pat], capture_output=True)

        self.url_box.value = "<i style='color:#888'>ComfyUI остановлен.</i>"
        self._set_status("🛑 ComfyUI остановлен. Можно запустить ячейку заново.",
                         "#e74c3c")
        self._print("[*] ComfyUI и туннель остановлены.")


def launch():
    """Создаёт лаунчер и запускает. Возвращает панель виджетов."""
    return ComfyLauncher().launch()


# При `%run start.py` запускаемся автоматически.
if __name__ == "__main__":
    launch()
