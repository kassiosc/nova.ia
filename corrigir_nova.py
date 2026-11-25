
from pathlib import Path
import re
import shutil

arquivo = Path("backend/main.py")
codigo = arquivo.read_text(encoding="utf-8")

# Ajustar Ollama
codigo, n1 = re.subn(
    r"def call_ollama\(messages\):",
    "def call_ollama(messages, timeout=180):",
    codigo,
    count=1
)

if n1 != 1:
    raise RuntimeError("Não encontrei call_ollama.")

inicio = codigo.index("def call_ollama(messages, timeout=180):")
fim = codigo.index("\ndef call_gemini", inicio)

parte = codigo[inicio:fim]
if "timeout=180," not in parte:
    raise RuntimeError("Timeout original do Ollama não encontrado.")

parte = parte.replace("timeout=180,", "timeout=timeout,", 1)
codigo = codigo[:inicio] + parte + codigo[fim:]

# Ajustar Gemini
codigo, n2 = re.subn(
    r"def call_gemini\(messages, json_mode=False\):",
    "def call_gemini(messages, json_mode=False, timeout=120):",
    codigo,
    count=1
)

if n2 != 1:
    raise RuntimeError("Não encontrei call_gemini.")

inicio = codigo.index("def call_gemini(messages, json_mode=False, timeout=120):")
fim = codigo.index('\n@app.post("/api/chat")', inicio)

parte = codigo[inicio:fim]
if "timeout=120," not in parte:
    raise RuntimeError("Timeout original do Gemini não encontrado.")

parte = parte.replace("timeout=120,", "timeout=timeout,", 1)
codigo = codigo[:inicio] + parte + codigo[fim:]

# Ajustar planejador
padrao = re.compile(
    r'    raw = ""\s+try:\s+'
    r'if GEMINI_API_KEY:.*?'
    r'(?=\s+try:\s+cleaned = raw\.strip\(\))',
    re.S
)

novo = '''    raw = ""

    try:
        if GEMINI_API_KEY:
            try:
                print("[NOVA] Consultando Gemini...")
                raw = call_gemini(
                    planner_messages,
                    json_mode=True,
                    timeout=25,
                )
            except Exception as gemini_error:
                print(f"[NOVA] Gemini falhou: {gemini_error}")
                print("[NOVA] Tentando Ollama Qwen 2.5 3B...")

                raw = call_ollama(
                    planner_messages,
                    timeout=60,
                )
        else:
            raw = call_ollama(
                planner_messages,
                timeout=60,
            )

    except Exception as error:
        raise HTTPException(
            503,
            f"Não foi possível acessar a IA planejadora: {str(error)[:500]}",
        ) from error
'''

codigo, n3 = padrao.subn(novo, codigo, count=1)

if n3 != 1:
    raise RuntimeError("Bloco do planejador não encontrado.")

# Validar antes de modificar o original
compile(codigo, str(arquivo), "exec")

backup = Path("backend/main.py.before_fallback.bak")

if backup.exists():
    raise RuntimeError("Backup já existe. Não será sobrescrito.")

shutil.copy2(arquivo, backup)
arquivo.write_text(codigo, encoding="utf-8")

print("SUCESSO: NOVA atualizada!")
print("Gemini: 25 segundos.")
print("Ollama: fallback automático.")
print("Backup criado.")
