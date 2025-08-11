#!/usr/bin/env bash
# Install dependencies for LangChain ↔ Ollama integration
# Reference: https://python.langchain.com/docs/integrations/chat/ollama/

set -euo pipefail

echo "[info] Using Python: $(command -v python || command -v python3)"
python - <<'PY'
import sys
print(f"[info] Python version: {sys.version.split()[0]}")
PY

echo "[step] Upgrading pip"
python -m pip install --upgrade pip

echo "[step] Installing langchain-ollama (preferred)"
python -m pip install -U langchain-ollama

echo "[verify] Verifying ChatOllama availability"
python - <<'PY'
try:
    from langchain_ollama import ChatOllama  # preferred package
    print("[ok] ChatOllama available via langchain-ollama")
except Exception as e:
    print(f"[warn] Could not import ChatOllama from langchain_ollama: {e}")
    print("[step] Installing fallback: langchain + langchain-community")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "langchain", "langchain-community"]) 
    try:
        from langchain_community.chat_models import ChatOllama  # fallback
        print("[ok] ChatOllama available via langchain-community")
    except Exception as e2:
        print(f"[error] ChatOllama not available after fallback install: {e2}")
        raise SystemExit(1)
PY

cat <<'NOTE'

[next]
- Ensure Ollama server is running locally (default http://localhost:11434)
- Pull a model if needed, e.g.:  ollama pull phi3.5:3.8b

[usage]
- Python snippet to test:
    from langchain_ollama import ChatOllama
    llm = ChatOllama(model="phi3.5:3.8b", temperature=0.2, base_url="http://localhost:11434")
    print(llm.invoke("Say hello").content)

  (If using fallback package):
    from langchain_community.chat_models import ChatOllama
    llm = ChatOllama(model="phi3.5:3.8b", temperature=0.2, base_url="http://localhost:11434")
    print(llm.invoke("Say hello").content)

NOTE

echo "[done] LangChain ↔ Ollama dependency setup complete"

