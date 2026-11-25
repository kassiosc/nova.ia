import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import requests
import uvicorn
import webview

HOST = "127.0.0.1"
PORT = 8000
OLLAMA_URL = "http://127.0.0.1:11434"

OLLAMA_MODELS_DIR = Path.home() / ".ollama" / "models"
OLLAMA_MODELS_DIR.mkdir(parents=True, exist_ok=True)
os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_DIR)

ollama_process = None


def find_ollama():
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Ollama" / "ollama.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Ollama" / "ollama.exe",
    ]

    located = shutil.which("ollama")
    if located:
        candidates.insert(0, Path(located))

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def ollama_is_ready():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return response.ok
    except requests.RequestException:
        return False


def start_ollama_if_needed():
    global ollama_process

    if ollama_is_ready():
        print("[NOVA] Ollama já está em execução.")
        return True

    executable = find_ollama()

    if not executable:
        print("[NOVA] Ollama não encontrado. O modo local ficará indisponível.")
        return False

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        ollama_process = subprocess.Popen(
            [executable, "serve"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            env=os.environ.copy(),
        )
    except OSError as error:
        print(f"[NOVA] Não foi possível iniciar o Ollama: {error}")
        ollama_process = None
        return False

    for _ in range(90):
        if ollama_is_ready():
            print("[NOVA] Ollama iniciado pela NOVA.")
            return True

        if ollama_process.poll() is not None:
            print("[NOVA] Processo do Ollama encerrado durante a inicialização.")
            ollama_process = None
            return False

        time.sleep(0.5)

    print("[NOVA] Tempo esgotado aguardando o Ollama.")
    stop_ollama_if_started()
    return False


def stop_ollama_if_started():
    global ollama_process

    process = ollama_process
    ollama_process = None

    if process is None or process.poll() is not None:
        return

    try:
        process.terminate()
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)
    except OSError as error:
        print(f"[NOVA] Erro ao encerrar Ollama: {error}")


from backend.main import app
from backend.permissions import grant_folder, list_authorized_folders, revoke_folder


class DesktopAPI:
    def select_folder(self):
        windows = webview.windows

        if not windows:
            return None

        result = windows[0].create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False,
        )

        if not result:
            return None

        selected = result[0] if isinstance(result, (list, tuple)) else result

        try:
            return {"path": grant_folder(str(selected))}
        except ValueError as error:
            raise RuntimeError(str(error))

    def get_authorized_folders(self):
        return list_authorized_folders()

    def revoke_folder(self, path):
        return revoke_folder(path)


server = uvicorn.Server(
    uvicorn.Config(
        app,
        host=HOST,
        port=PORT,
        log_level="warning",
        access_log=False,
    )
)


def start_backend():
    server.run()


def wait_for_backend():
    url = f"http://{HOST}:{PORT}/api/health"

    for _ in range(60):
        try:
            response = requests.get(url, timeout=1)
            if response.ok:
                return True
        except requests.RequestException:
            pass

        time.sleep(0.5)

    return False


def main():
    start_ollama_if_needed()

    backend_thread = threading.Thread(
        target=start_backend,
        daemon=True,
    )
    backend_thread.start()

    if not wait_for_backend():
        server.should_exit = True
        stop_ollama_if_started()
        raise RuntimeError(
            "A NOVA AI não conseguiu iniciar o servidor local. "
            "Verifique se a porta 8000 está livre."
        )

    webview.create_window(
        title="NOVA AI",
        url=f"http://{HOST}:{PORT}",
        width=1280,
        height=820,
        min_size=(900, 600),
        background_color="#080d18",
        js_api=DesktopAPI(),
    )

    try:
        webview.start()
    finally:
        server.should_exit = True
        stop_ollama_if_started()


if __name__ == "__main__":
    main()
