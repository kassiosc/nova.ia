from pathlib import Path
from datetime import datetime
import shutil
import re

ROOT = Path(r"D:\Luan\Projetos Integradores\NOVA-AI")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend" / "src"

FILES = [
    BACKEND / "permissions.py",
    BACKEND / "tools.py",
    BACKEND / "desktop.py",
    BACKEND / "main.py",
    FRONTEND / "App.tsx",
    FRONTEND / "App.css",
]

for file in FILES:
    if not file.exists():
        raise SystemExit(f"Arquivo não encontrado: {file}")

backup_dir = ROOT / "backups" / ("antes_atualizacao_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
backup_dir.mkdir(parents=True)

for file in FILES:
    shutil.copy2(file, backup_dir / file.name)

print(f"Backups criados em: {backup_dir}")

def read(path):
    return path.read_text(encoding="utf-8-sig")

def write(path, content):
    path.write_text(content, encoding="utf-8")

# --------------------------------------------------
# 1. PERMISSOES DE PASTAS
# --------------------------------------------------

permissions = r'''import json
import os
from pathlib import Path
from threading import RLock

from fastapi import HTTPException

DATA_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home()))
) / "NOVA-AI"

WORKSPACE = DATA_DIR / "workspace"
PERMISSIONS_FILE = DATA_DIR / "authorized_folders.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE.mkdir(parents=True, exist_ok=True)

_lock = RLock()


def _load_grants():
    try:
        data = json.loads(PERMISSIONS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_grants(paths):
    temporary = PERMISSIONS_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(paths, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(PERMISSIONS_FILE)


def authorized_roots():
    roots = [WORKSPACE.resolve()]

    with _lock:
        for raw in _load_grants():
            try:
                path = Path(raw).resolve(strict=True)
                if path.is_dir() and path not in roots:
                    roots.append(path)
            except (OSError, RuntimeError, ValueError):
                continue

    return roots


def list_authorized_folders():
    return [
        str(path)
        for path in authorized_roots()
    ]


def grant_folder(raw_path: str):
    if not raw_path or "\x00" in raw_path:
        raise ValueError("Pasta inválida.")

    try:
        folder = Path(raw_path).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise ValueError("Não foi possível localizar essa pasta.")

    if not folder.is_dir():
        raise ValueError("O caminho escolhido não é uma pasta.")

    # Não autoriza uma unidade inteira, como C:\ ou D:\.
    if folder.parent == folder:
        raise ValueError("Selecione uma pasta dentro da unidade, não a unidade inteira.")

    workspace = WORKSPACE.resolve()

    if folder == workspace or workspace in folder.parents:
        return str(folder)

    with _lock:
        paths = _load_grants()

        normalized = {
            str(Path(item).resolve()).casefold()
            for item in paths
        }

        if str(folder).casefold() not in normalized:
            paths.append(str(folder))
            _save_grants(paths)

    return str(folder)


def revoke_folder(raw_path: str):
    try:
        target = Path(raw_path).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise ValueError("Pasta não encontrada.")

    if target == WORKSPACE.resolve():
        raise ValueError("O workspace não pode ser removido das permissões.")

    with _lock:
        paths = _load_grants()
        filtered = []

        for item in paths:
            try:
                if Path(item).resolve() != target:
                    filtered.append(item)
            except (OSError, RuntimeError, ValueError):
                continue

        _save_grants(filtered)

    return {"success": True, "path": str(target)}


def authorized_path(raw_path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
        raise HTTPException(400, "Caminho inválido.")

    supplied = Path(raw_path)

    if ".." in supplied.parts:
        raise HTTPException(403, "Caminhos com '..' não são permitidos.")

    try:
        candidate = supplied.resolve() if supplied.is_absolute() else (WORKSPACE / supplied).resolve()
    except (OSError, RuntimeError, ValueError):
        raise HTTPException(400, "Não foi possível validar o caminho.")

    for root in authorized_roots():
        if candidate == root or root in candidate.parents:
            return candidate

    raise HTTPException(
        403,
        "Acesso negado. Selecione e autorize essa pasta primeiro.",
    )
'''

write(BACKEND / "permissions.py", permissions)

# --------------------------------------------------
# 2. FERRAMENTAS DE ARQUIVOS
# --------------------------------------------------

tools = r'''import ipaddress
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from send2trash import send2trash
from fastapi import HTTPException

from backend.permissions import (
    WORKSPACE,
    authorized_path,
    authorized_roots,
)

MAX_READ_SIZE = 1_000_000
MAX_DOWNLOAD_SIZE = 25 * 1024 * 1024

TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".xml", ".html", ".css",
    ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".c", ".cpp",
    ".h", ".sql", ".yaml", ".yml", ".toml", ".ini", ".log",
    ".env.example", ".bat", ".ps1"
}


def list_files(path="."):
    folder = authorized_path(path)

    if not folder.exists() or not folder.is_dir():
        raise HTTPException(404, "Pasta não encontrada.")

    items = []

    try:
        entries = sorted(folder.iterdir(), key=lambda item: item.name.lower())

        for item in entries:
            try:
                if item.is_symlink():
                    continue

                items.append({
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            except OSError:
                continue

    except PermissionError:
        raise HTTPException(403, "Sem permissão para listar essa pasta.")

    return {"path": str(folder), "items": items}


def read_file(path):
    file = authorized_path(path)

    if not file.exists() or not file.is_file():
        raise HTTPException(404, "Arquivo não encontrado.")

    if file.suffix.lower() not in TEXT_EXTENSIONS:
        raise HTTPException(415, "Formato não permitido para leitura como texto.")

    if file.stat().st_size > MAX_READ_SIZE:
        raise HTTPException(413, "Arquivo muito grande para leitura.")

    try:
        content = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "O arquivo não está codificado em UTF-8.")

    return {"path": str(file), "content": content}


def create_file(path, content):
    file = authorized_path(path)

    if file.exists():
        raise HTTPException(409, "O arquivo já existe.")

    if file.suffix.lower() not in TEXT_EXTENSIONS:
        raise HTTPException(415, "Extensão não permitida.")

    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")

    return {"success": True, "path": str(file)}


def edit_file(path, content):
    file = authorized_path(path)

    if not file.exists() or not file.is_file():
        raise HTTPException(404, "Arquivo não encontrado.")

    if file.suffix.lower() not in TEXT_EXTENSIONS:
        raise HTTPException(415, "Extensão não permitida.")

    if file.stat().st_size > MAX_READ_SIZE:
        raise HTTPException(413, "Arquivo muito grande para edição.")

    file.write_text(content, encoding="utf-8")

    return {"success": True, "path": str(file)}


def create_folder(path):
    folder = authorized_path(path)

    if folder.exists():
        raise HTTPException(409, "Já existe um item com esse nome.")

    folder.mkdir(parents=True, exist_ok=False)

    return {"success": True, "path": str(folder)}


def move_file(source, destination):
    original = authorized_path(source)
    target = authorized_path(destination)

    if not original.exists():
        raise HTTPException(404, "Origem não encontrada.")

    if target.exists():
        raise HTTPException(409, "O destino já existe.")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(original), str(target))

    return {
        "success": True,
        "source": str(original),
        "destination": str(target),
    }


def delete_file(path):
    target = authorized_path(path)

    if not target.exists():
        raise HTTPException(404, "Item não encontrado.")

    if any(target == root for root in authorized_roots()):
        raise HTTPException(403, "Uma pasta autorizada não pode ser excluída como raiz.")

    send2trash(str(target))

    return {
        "success": True,
        "message": "Item enviado para a Lixeira.",
    }


def validate_download_url(url):
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(400, "Somente downloads por HTTPS são permitidos.")

    host = parsed.hostname.lower()

    if host in ("localhost", "localhost.localdomain"):
        raise HTTPException(403, "Endereço local não permitido.")

    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(400, "Não foi possível localizar o servidor.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast
        ):
            raise HTTPException(403, "Endereço de rede não permitido.")


def download_file(url, destination):
    validate_download_url(url)
    target = authorized_path(destination)

    if target.exists():
        raise HTTPException(409, "Já existe um item com esse nome.")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".download")

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(10, 30),
            allow_redirects=False,
        ) as response:
            response.raise_for_status()

            if 300 <= response.status_code < 400:
                raise HTTPException(400, "Redirecionamentos não são permitidos.")

            total = 0

            with temporary.open("wb") as output:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_DOWNLOAD_SIZE:
                        raise HTTPException(413, "Download excede o limite de 25 MB.")

                    output.write(chunk)

        temporary.replace(target)

    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    return {
        "success": True,
        "path": str(target),
        "size": total,
    }


def run_command(command, cwd=None):
    if not command or not isinstance(command, list):
        raise HTTPException(400, "Comando inválido.")

    if not all(isinstance(arg, str) for arg in command):
        raise HTTPException(400, "Argumentos inválidos.")

    if len(command) > 15 or any(len(arg) > 300 for arg in command):
        raise HTTPException(400, "Comando excede os limites permitidos.")

    executable = command[0].lower()

    if executable == "python":
        if command[1:] not in (["--version"], ["-m", "compileall", "."]):
            raise HTTPException(403, "Comando Python não autorizado.")

        final_command = [sys.executable] + command[1:]

    elif executable == "node":
        if command[1:] != ["--version"]:
            raise HTTPException(403, "Comando Node não autorizado.")

        executable_path = shutil.which("node")
        if not executable_path:
            raise HTTPException(503, "Node.js não encontrado.")

        final_command = [executable_path] + command[1:]

    elif executable == "npm":
        if command[1:] not in (["--version"], ["run", "build"], ["run", "test"]):
            raise HTTPException(403, "Comando npm não autorizado.")

        executable_path = shutil.which("npm")
        if not executable_path:
            raise HTTPException(503, "npm não encontrado.")

        final_command = [executable_path] + command[1:]

    else:
        raise HTTPException(403, "Esse programa não está na lista autorizada.")

    working_dir = authorized_path(cwd) if cwd else WORKSPACE.resolve()

    if not working_dir.is_dir():
        raise HTTPException(400, "A pasta de execução não existe.")

    try:
        result = subprocess.run(
            final_command,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "O comando excedeu o limite de 60 segundos.")

    return {
        "return_code": result.returncode,
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-12000:],
    }


def execute_action(action, arguments):
    if action == "list_files":
        return list_files(arguments.get("path", "."))

    if action == "read_file":
        return read_file(arguments["path"])

    if action == "create_file":
        return create_file(arguments["path"], arguments["content"])

    if action == "edit_file":
        return edit_file(arguments["path"], arguments["content"])

    if action == "create_folder":
        return create_folder(arguments["path"])

    if action == "move_file":
        return move_file(arguments["source"], arguments["destination"])

    if action == "delete_file":
        return delete_file(arguments["path"])

    if action == "download_file":
        return download_file(arguments["url"], arguments["destination"])

    if action == "run_command":
        return run_command(arguments["command"], arguments.get("cwd"))

    raise HTTPException(400, "Ferramenta desconhecida.")
'''

write(BACKEND / "tools.py", tools)

# --------------------------------------------------
# 3. INTEGRACAO COM O SELETOR NATIVO DO WINDOWS
# --------------------------------------------------

desktop = r'''import threading
import time

import requests
import uvicorn
import webview

from backend.main import app
from backend.permissions import grant_folder, list_authorized_folders, revoke_folder

HOST = "127.0.0.1"
PORT = 8000


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
    backend_thread = threading.Thread(
        target=start_backend,
        daemon=True,
    )
    backend_thread.start()

    if not wait_for_backend():
        server.should_exit = True
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


if __name__ == "__main__":
    main()
'''

write(BACKEND / "desktop.py", desktop)

# --------------------------------------------------
# 4. ATUALIZAR ROTAS E PLANEJADOR
# --------------------------------------------------

main_path = BACKEND / "main.py"
main = read(main_path)

old_route = '''@app.get("/api/files")
def list_files(profile: str = Header(default="principal", alias="X-Profile")):
    items = []

    for item in sorted(WORKSPACE.iterdir(), key=lambda x: x.name.lower()):
        items.append({"name": item.name, "type": "folder" if item.is_dir() else "file"})

    return {"workspace": str(WORKSPACE), "items": items}
'''

new_route = '''@app.get("/api/files")
def list_files(
    path: str = ".",
    profile: str = Header(default="principal", alias="X-Profile"),
):
    data = execute_action("list_files", {"path": path})

    return {
        "workspace": str(WORKSPACE),
        "current_path": data["path"],
        "items": data["items"],
    }
'''

if old_route not in main:
    raise SystemExit("Não encontrei a rota /api/files esperada. Nenhuma alteração adicional foi aplicada.")

main = main.replace(old_route, new_route, 1)

old_import = "from backend.tools import execute_action"
if old_import not in main:
    raise SystemExit("Import de execute_action não encontrado.")

main = main.replace(
    old_import,
    "from backend.tools import execute_action\nfrom backend.permissions import list_authorized_folders",
    1,
)

old_allowed = '''    "create_file",
    "edit_file",
    "move_file",'''
new_allowed = '''    "create_file",
    "edit_file",
    "create_folder",
    "move_file",'''

if old_allowed not in main:
    raise SystemExit("Não encontrei a lista de ações autorizadas.")

main = main.replace(old_allowed, new_allowed, 1)

old_prompt = '''4. edit_file: {"path": "arquivo.txt", "content": "texto"}
5. move_file: {"source": "origem.txt", "destination": "destino.txt"}
6. delete_file: {"path": "arquivo.txt"}
7. download_file: {"url": "https://...", "destination": "arquivo.zip"}
8. run_command: {"command": ["npm", "--version"]}

Regras:
- Só use essas ferramentas.
- Todos os caminhos são relativos à pasta workspace.'''

new_prompt = '''4. edit_file: {"path": "arquivo.txt", "content": "texto"}
5. create_folder: {"path": "nova_pasta"}
6. move_file: {"source": "origem.txt", "destination": "destino.txt"}
7. delete_file: {"path": "arquivo.txt"}
8. download_file: {"url": "https://...", "destination": "arquivo.zip"}
9. run_command: {"command": ["npm", "--version"], "cwd": "."}

Regras:
- Só use essas ferramentas.
- Os caminhos podem ser relativos ao workspace ou absolutos dentro de uma pasta autorizada pelo usuário.
- Nunca tente acessar caminhos fora das pastas autorizadas.'''

if old_prompt not in main:
    raise SystemExit("Não encontrei o trecho esperado do planejador.")

main = main.replace(old_prompt, new_prompt, 1)
write(main_path, main)

# --------------------------------------------------
# 5. FRONTEND: MARKDOWN, SELETOR E NAVEGACAO
# --------------------------------------------------

app_path = FRONTEND / "App.tsx"
app = read(app_path)

if 'import ReactMarkdown from "react-markdown";' not in app:
    app = app.replace(
        'import { useEffect, useRef, useState, type FormEvent } from "react";',
        'import { useEffect, useRef, useState, type FormEvent } from "react";\n'
        'import ReactMarkdown from "react-markdown";\n'
        'import remarkGfm from "remark-gfm";',
        1,
    )

app = app.replace(
    'FileText, Folder, HardDrive, MessageSquare, Monitor,',
    'FileText, Folder, FolderOpen, HardDrive, MessageSquare, Monitor,',
    1,
)

if "declare global {" not in app:
    app = app.replace(
        'const API = "http://127.0.0.1:8000";',
        '''const API = "http://127.0.0.1:8000";

declare global {
  interface Window {
    pywebview?: {
      api?: {
        select_folder: () => Promise<{ path: string } | null>;
        get_authorized_folders: () => Promise<string[]>;
        revoke_folder: (path: string) => Promise<unknown>;
      };
    };
  }
}''',
        1,
    )

app = app.replace(
    '  const [workspace, setWorkspace] = useState("");',
    '''  const [workspace, setWorkspace] = useState("");
  const [currentFolder, setCurrentFolder] = useState("");
  const [folderRoot, setFolderRoot] = useState("");
  const [folderLoading, setFolderLoading] = useState(false);''',
    1,
)

# Mantém o workspace inicial e evita resetar a navegação a cada atualização automática.
app = app.replace(
    '      setWorkspace(fileData.workspace || "");',
    '''      setWorkspace(fileData.workspace || "");
      if (!currentFolder) {
        setCurrentFolder(fileData.workspace || "");
        setFolderRoot(fileData.workspace || "");
      }''',
    1,
)

anchor = '''  useEffect(() => {
    loadData();'''
functions = '''  async function loadFolder(path: string) {
    if (!path) return;

    setFolderLoading(true);

    try {
      const data = await api<any>(
        `/api/files?path=${encodeURIComponent(path)}`
      );

      setFiles(data.items || []);
      setCurrentFolder(data.current_path || path);
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Não foi possível abrir a pasta.");
    } finally {
      setFolderLoading(false);
    }
  }

  async function chooseFolder() {
    try {
      const bridge = window.pywebview?.api;

      if (!bridge) {
        setNotice("O seletor de pastas está disponível ao abrir a NOVA pelo aplicativo desktop.");
        return;
      }

      const selected = await bridge.select_folder();

      if (selected?.path) {
        setFolderRoot(selected.path);
        await loadFolder(selected.path);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Não foi possível selecionar a pasta.");
    }
  }

  async function returnToFolderRoot() {
    if (folderRoot) {
      await loadFolder(folderRoot);
    }
  }

  async function returnToWorkspace() {
    setFolderRoot(workspace);
    await loadFolder(workspace);
  }

'''
if anchor not in app:
    raise SystemExit("Não encontrei o ponto de inserção das funções do frontend.")

app = app.replace(anchor, functions + anchor, 1)

# Markdown nas respostas do assistente; mensagens do usuário continuam em texto simples.
if '{message.content}' not in app:
    raise SystemExit("Não encontrei a renderização do conteúdo das mensagens.")

app = app.replace(
    '{message.content}',
    '''{message.role === "assistant" ? (
     <div className="nova-markdown">
       <ReactMarkdown remarkPlugins={[remarkGfm]}>
         {message.content}
       </ReactMarkdown>
     </div>
   ) : message.content}''',
    1,
)

old_page = '''        {page === "files" && (
          <div style={{ flex: 1, overflowY: "auto", padding: 25 }}>
            <div style={{ maxWidth: 850, margin: "0 auto" }}>
              <h2>Arquivos do workspace</h2>
              <p style={styles.muted}>{workspace}</p>
              <div style={styles.secondary}>
                {files.map((file) => (
                  <div key={file.name} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: 12, borderBottom: "1px solid #292b34",
                  }}>
                    {file.type === "folder" ? <Folder size={18} color="#a99aff" /> : <FileText size={18} />}
                    <span style={{ flex: 1, fontSize: 13 }}>{file.name}</span>
                    <span style={styles.muted}>{file.type === "folder" ? "Pasta" : formatBytes(file.size)}</span>
                  </div>
                ))}
                {files.length === 0 && <p style={styles.muted}>Nenhum arquivo encontrado.</p>}
              </div>
            </div>
          </div>
        )}'''

new_page = '''        {page === "files" && (
          <div style={{ flex: 1, overflowY: "auto", padding: 25 }}>
            <div style={{ maxWidth: 950, margin: "0 auto", display: "grid", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <h2 style={{ marginBottom: 6 }}>Explorador de arquivos</h2>
                  <p style={styles.muted}>A NOVA só acessa pastas escolhidas e autorizadas por você.</p>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button style={styles.button} onClick={returnToWorkspace}>
                    <HardDrive size={15} /> Workspace
                  </button>
                  <button style={{ ...styles.button, background: "#705cf6" }} onClick={chooseFolder}>
                    <FolderOpen size={15} /> Selecionar pasta
                  </button>
                  <button style={styles.button} onClick={() => loadFolder(currentFolder || workspace)} disabled={folderLoading}>
                    <RefreshCw size={15} /> Atualizar
                  </button>
                </div>
              </div>

              <section style={styles.secondary}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                  <Folder size={17} color="#a99aff" />
                  <span style={{ fontSize: 12, overflowWrap: "anywhere" }}>{currentFolder || workspace}</span>
                </div>

                {folderRoot && currentFolder && currentFolder !== folderRoot && (
                  <button style={{ ...styles.button, marginBottom: 12 }} onClick={returnToFolderRoot}>
                    Voltar à pasta selecionada
                  </button>
                )}

                {files.map((file) => (
                  <div key={file.name} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: 12, borderTop: "1px solid #292b34",
                  }}>
                    {file.type === "folder"
                      ? <Folder size={18} color="#a99aff" />
                      : <FileText size={18} />}
                    {file.type === "folder" ? (
                      <button
                        onClick={() => loadFolder(`${currentFolder}\\\\${file.name}`)}
                        style={{ flex: 1, textAlign: "left", color: "#ececf1", background: "transparent", border: 0, cursor: "pointer", fontSize: 13, padding: 0 }}
                      >
                        {file.name}
                      </button>
                    ) : (
                      <span style={{ flex: 1, fontSize: 13, overflowWrap: "anywhere" }}>{file.name}</span>
                    )}
                    <span style={styles.muted}>
                      {file.type === "folder" ? "Pasta" : formatBytes(file.size)}
                    </span>
                  </div>
                ))}

                {files.length === 0 && (
                  <p style={styles.muted}>
                    {folderLoading ? "Carregando..." : "Nenhum arquivo encontrado nesta pasta."}
                  </p>
                )}
              </section>
            </div>
          </div>
        )}'''

if old_page not in app:
    raise SystemExit("Não encontrei a tela de arquivos esperada.")

app = app.replace(old_page, new_page, 1)
write(app_path, app)

# --------------------------------------------------
# 6. ESTILOS DO MARKDOWN
# --------------------------------------------------

css_path = FRONTEND / "App.css"
css = read(css_path)

if ".nova-markdown" not in css:
    css += r'''

/* Respostas formatadas da NOVA AI */
.nova-markdown {
  user-select: text;
  -webkit-user-select: text;
  overflow-wrap: anywhere;
  line-height: 1.75;
}

.nova-markdown p {
  margin: 0 0 12px;
}

.nova-markdown p:last-child {
  margin-bottom: 0;
}

.nova-markdown h1,
.nova-markdown h2,
.nova-markdown h3,
.nova-markdown h4 {
  color: #f4f2ff;
  line-height: 1.35;
  margin: 18px 0 9px;
}

.nova-markdown h1 { font-size: 21px; }
.nova-markdown h2 { font-size: 18px; }
.nova-markdown h3 { font-size: 16px; }

.nova-markdown ul,
.nova-markdown ol {
  padding-left: 24px;
  margin: 8px 0 14px;
}

.nova-markdown li {
  padding-left: 3px;
  margin: 4px 0;
}

.nova-markdown strong {
  color: #fff;
  font-weight: 700;
}

.nova-markdown blockquote {
  border-left: 3px solid #705cf6;
  margin: 12px 0;
  padding: 8px 14px;
  color: #b9bac6;
  background: #15171e;
  border-radius: 0 8px 8px 0;
}

.nova-markdown pre {
  overflow-x: auto;
  padding: 14px;
  border: 1px solid #30323e;
  border-radius: 9px;
  background: #101116;
  margin: 12px 0;
}

.nova-markdown code {
  font-family: Consolas, monospace;
  font-size: .9em;
}

.nova-markdown :not(pre) > code {
  background: #252632;
  border-radius: 4px;
  padding: 2px 5px;
}

.nova-markdown a {
  color: #a99aff;
  text-decoration: underline;
}

.nova-markdown table {
  border-collapse: collapse;
  width: 100%;
  display: block;
  overflow-x: auto;
  margin: 12px 0;
}

.nova-markdown th,
.nova-markdown td {
  border: 1px solid #393b46;
  padding: 8px 10px;
  text-align: left;
}

.nova-markdown th {
  background: #202127;
}
'''
    write(css_path, css)

print("Arquivos atualizados.")
print("Backup:", backup_dir)
