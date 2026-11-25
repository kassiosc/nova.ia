import json
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
