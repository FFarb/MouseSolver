# GPT Hotkey Application

A Windows desktop helper that sends highlighted text to the OpenAI Responses API with a single hotkey and places the response back onto the clipboard.

## Features

- Global hotkeys powered by the [`keyboard`](https://github.com/boppreh/keyboard) library:
  - **F8** – capture the current selection, send it to OpenAI, and copy the reply back to the clipboard.
  - **F12** – terminate the application immediately.
- System tray icon with status notifications via `pystray`.
- Clipboard preservation using `pyperclip`.
- Invisible text selection to avoid flashing.
- Socket-based single-instance lock to prevent multiple instances from running.
- Structured logging to both console and a rotating file.

## Configuration

Copy `.env.example` to `.env` and update the values:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5
SYSTEM_PROMPT=You are a concise helpful assistant.
REQUEST_TIMEOUT=30
LOG_LEVEL=INFO
```

The application exits immediately if `OPENAI_API_KEY` is missing. The `OPENAI_MODEL` defaults to `gpt-5` if not set.

## Installation & Running Locally

All commands below assume you are at the project root (the folder that contains the `gpt_hotkey_app/` package and `pyproject.toml`).

```bash
python -m venv .venv
. .venv/Scripts/activate  # On Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r gpt_hotkey_app/requirements.txt
python -m gpt_hotkey_app.main
```

## Building a Standalone Executable

The project is designed to work well with PyInstaller:

```bash
pyinstaller --noconfirm --onefile --windowed --name GPT-Hotkey gpt_hotkey_app/main.py
```

## Logging

Logs are written to `gpt_hotkey_app.log` in the current working directory. Adjust the verbosity with the `LOG_LEVEL` environment variable.
