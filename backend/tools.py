import ipaddress
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
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

    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_READ_SIZE:
        raise HTTPException(413, "O conteúdo excede o limite permitido.")
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(f".{file.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, file)
        except FileExistsError:
            raise HTTPException(409, "O arquivo já existe.")
    finally:
        if temporary.exists():
            temporary.unlink()

    return {"success": True, "path": str(file)}


def edit_file(path, content, expected_hash=None):
    file = authorized_path(path)

    if not file.exists() or not file.is_file():
        raise HTTPException(404, "Arquivo não encontrado.")

    if file.suffix.lower() not in TEXT_EXTENSIONS:
        raise HTTPException(415, "Extensão não permitida.")

    if file.stat().st_size > MAX_READ_SIZE:
        raise HTTPException(413, "Arquivo muito grande para edição.")

    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_READ_SIZE:
        raise HTTPException(413, "O conteúdo novo excede o limite de edição.")
    original = file.read_bytes()
    actual_hash = hashlib.sha256(original).hexdigest()
    if not expected_hash or actual_hash != expected_hash:
        raise HTTPException(409, "O arquivo mudou desde a preparação. Prepare uma nova proposta antes de editar.")

    temporary = file.with_name(f".{file.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected_hash:
            raise HTTPException(409, "O arquivo mudou durante a edição. Prepare uma nova proposta.")
        temporary.replace(file)
        if file.read_text(encoding="utf-8") != content:
            raise HTTPException(500, "A verificação após a gravação falhou.")
    finally:
        if temporary.exists():
            temporary.unlink()

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

    if original == target or original in target.parents:
        raise HTTPException(400, "Não é possível mover uma pasta para dentro dela mesma.")
    if not original.is_dir() and target.is_dir():
        target = target / original.name
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
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".download", dir=target.parent)
    temporary = Path(temporary_name)

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

            with os.fdopen(descriptor, "wb") as output:
                descriptor = None
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_DOWNLOAD_SIZE:
                        raise HTTPException(413, "Download excede o limite de 25 MB.")

                    output.write(chunk)

        try:
            os.link(temporary, target)
        except FileExistsError:
            raise HTTPException(409, "O destino já existe; nenhum arquivo foi sobrescrito.")

    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
        raise

    if temporary.exists():
        temporary.unlink()

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

    if result.returncode != 0:
        explanation = (result.stderr or result.stdout or "O processo terminou com erro.")[-1500:]
        raise HTTPException(400, f"O comando falhou (código {result.returncode}): {explanation}")

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
        return edit_file(arguments["path"], arguments["content"], arguments.get("expected_hash"))

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

    if action == "search_apps":
        return search_apps(arguments["query"])

    if action == "install_app":
        return install_app(arguments["package_id"])
    raise HTTPException(400, "Ferramenta desconhecida.")
import re

WINGET_SEARCHED_IDS = set()
MAX_APP_SEARCH_RESULTS = 100


def get_winget_path():
    executable = shutil.which("winget")
    if not executable:
        raise HTTPException(503, "WinGet não encontrado.")
    return executable


def search_apps(query):
    if not isinstance(query, str) or not query.strip() or len(query) > 100:
        raise HTTPException(400, "Termo de pesquisa inválido.")

    search_term = query.strip()

    if "." in search_term and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", search_term):
        search_args = ["--id", search_term, "--exact"]
    else:
        search_args = ["--query", search_term]

    command = [
        get_winget_path(), "search",
        *search_args,
        "--source", "winget",
        "--count", str(MAX_APP_SEARCH_RESULTS),
        "--accept-source-agreements",
        "--disable-interactivity",
    ]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True,
            timeout=45, shell=False, check=False,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Tempo limite da pesquisa.")

    if result.returncode != 0:
        raise HTTPException(400, (result.stderr or result.stdout)[-1200:])

    apps = []
    WINGET_SEARCHED_IDS.clear()

    for line in result.stdout.splitlines():
        if "." in search_term and search_term in line:
            package_id = search_term
            id_position = line.find(package_id)
            name = line[:id_position].strip()
            version = line[id_position + len(package_id):].strip()
            if not name or not version:
                continue
        else:
            columns = re.split(r"\s{2,}", line.strip())
            if len(columns) < 3:
                continue

            name, package_id, version = columns[:3]

        version = version.split(" Moniker:", 1)[0].split(" ProductCode:", 1)[0].strip()

        if package_id.lower() == "id":
            continue

        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", package_id):
            continue

        WINGET_SEARCHED_IDS.add(package_id)
        apps.append({
            "name": name,
            "id": package_id,
            "version": version,
            "source": "winget",
        })

    def language_priority(app):
        name = app["name"].casefold()
        package_id = app["id"].casefold()

        if "pt-br" in name or package_id.endswith(".pt-br"):
            return 0
        if "msix" in name or package_id.endswith(".msix"):
            return 2
        if re.search(r"\\([a-z]{2,3}(?:-[a-z]{2})?\\)$", name):
            return 3
        return 1

    apps.sort(key=language_priority)

    return {"query": query.strip(), "count": len(apps), "apps": apps}


def install_app(package_id):
    if not isinstance(package_id, str) or package_id not in WINGET_SEARCHED_IDS:
        raise HTTPException(403, "Aplicativo não encontrado em pesquisa recente.")

    winget = get_winget_path()

    installed = subprocess.run(
        [winget, "list", "--id", package_id, "--exact",
         "--source", "winget", "--disable-interactivity"],
        capture_output=True, text=True, timeout=60,
        shell=False, check=False, encoding="utf-8", errors="replace",
    )

    if installed.returncode != 0 and (installed.returncode & 0xFFFFFFFF) != 0x8A150014:
        raise HTTPException(400, "Não foi possível verificar se o aplicativo já está instalado.")

    installed_lines = installed.stdout.splitlines()
    already_installed = any(
        package_id.casefold() in line.casefold()
        for line in installed_lines
    )

    if already_installed:
        WINGET_SEARCHED_IDS.discard(package_id)
        return {
            "success": True,
            "already_installed": True,
            "package_id": package_id,
            "message": f"O aplicativo já está instalado: {package_id}",
            "output": installed.stdout[-3000:],
        }

    validation = subprocess.run(
        [winget, "show", "--id", package_id, "--exact",
         "--source", "winget", "--accept-source-agreements",
         "--disable-interactivity"],
        capture_output=True, text=True, timeout=60,
        shell=False, check=False, encoding="utf-8", errors="replace",
    )

    if validation.returncode != 0:
        raise HTTPException(400, "Pacote não validado pelo WinGet.")

    result = subprocess.run(
        [winget, "install", "--id", package_id, "--exact",
         "--source", "winget", "--accept-source-agreements",
         "--accept-package-agreements", "--disable-interactivity"],
        capture_output=True, text=True, timeout=900,
        shell=False, check=False, encoding="utf-8", errors="replace",
    )

    if result.returncode != 0:
        raise HTTPException(400, (result.stderr or result.stdout)[-1500:])

    WINGET_SEARCHED_IDS.discard(package_id)

    return {
        "success": True,
        "already_installed": False,
        "package_id": package_id,
        "message": f"Instalação concluída: {package_id}",
        "output": result.stdout[-3000:],
    }
