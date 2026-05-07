import json
from pathlib import Path
from typing import Optional, Dict

# 📁 Arquivo será criado na raiz do projeto
FILE_PATH = Path("holyrics_config.json")


def load_config() -> Optional[Dict]:
    """
    Carrega a configuração do Holyrics.

    Retorna:
        dict com config ou None se não existir.
    """
    try:
        if not FILE_PATH.exists():
            return None

        content = FILE_PATH.read_text(encoding="utf-8").strip()

        if not content:
            return None

        return json.loads(content)

    except Exception:
        # 🔥 Se o arquivo estiver corrompido, não quebra o sistema
        return None


def save_config(data: Dict) -> None:
    """
    Salva a configuração do Holyrics de forma segura.
    """

    # 🔒 Garante apenas os campos esperados
    payload = {
        "host": data.get("host", "localhost"),
        "port": int(data.get("port", 8091)),
        "token": data.get("token", ""),
    }

    # 📁 Cria diretório se necessário (caso mude no futuro)
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 🔥 Escrita segura (evita corromper arquivo)
    temp_file = FILE_PATH.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    temp_file.replace(FILE_PATH)


def is_configured() -> bool:
    """
    Verifica se já existe configuração válida.
    """
    data = load_config()

    if not data:
        return False

    return bool(data.get("host") and data.get("port"))