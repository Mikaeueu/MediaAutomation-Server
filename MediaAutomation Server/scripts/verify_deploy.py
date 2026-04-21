#!/usr/bin/env python3
"""
scripts/verify_deploy.py

Validação pré-build para ambiente de produção:
- Verifica app/config.json (estrutura mínima e valores)
- Verifica app/requirements.txt (presença de pacotes essenciais)
- Verifica existência de secrets apontados no config

Exit codes:
 0 = OK
 1 = Erro crítico (falha que impede build)
 2 = Avisos (não bloqueante) — script retorna 0 para permitir build, mas imprime avisos
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
CONFIG_PATH = APP_DIR / "config.json"
REQS_PATH = APP_DIR / "requirements.txt"

# Pacotes essenciais esperados no requirements.txt
ESSENTIAL_PKGS = {"fastapi", "uvicorn", "pydantic", "cryptography"}
# Pacotes de desenvolvimento que não deveriam estar em produção (apenas aviso)
DEV_PKGS = {"pytest", "black", "mypy", "flake8", "pre-commit", "pytest-asyncio"}
# Pacotes opcionais que o config pode requerer (ex.: OAuth)
OAUTH_PKGS = {"google-auth", "google-auth-oauthlib", "google-api-python-client"}

# Helpers para cores (se terminal suportar)
def c(text, color_code):
    try:
        return f"\033[{color_code}m{text}\033[0m"
    except Exception:
        return text

def ok(msg):
    print(c("[OK] ", "32") + msg)

def warn(msg):
    print(c("[WARN] ", "33") + msg)

def err(msg):
    print(c("[ERROR] ", "31") + msg)

def read_requirements(path: Path):
    if not path.exists():
        return None
    lines = []
    with path.open("r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            # remove extras like ==version or >=
            pkg = ln.split("==")[0].split(">=")[0].split("<=")[0].split()[0]
            lines.append(pkg)
    return set(lines)

def main():
    critical = False
    warnings = []

    print("Verificando arquivos de deploy (produção)...")
    # 1) Verifica existência dos arquivos
    if not CONFIG_PATH.exists():
        err(f"Arquivo de configuração não encontrado: {CONFIG_PATH}")
        sys.exit(1)
    else:
        ok(f"Encontrado config: {CONFIG_PATH}")

    if not REQS_PATH.exists():
        err(f"Arquivo requirements não encontrado: {REQS_PATH}")
        sys.exit(1)
    else:
        ok(f"Encontrado requirements: {REQS_PATH}")

    # 2) Valida JSON
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        ok("config.json é um JSON válido")
    except Exception as e:
        err(f"Falha ao parsear config.json: {e}")
        sys.exit(1)

    # 3) Checa chaves mínimas
    def has_path(d, path_list):
        cur = d
        for p in path_list:
            if not isinstance(cur, dict) or p not in cur:
                return False
            cur = cur[p]
        return True

    required_paths = [
        ("obs.host", ["obs", "host"]),
        ("obs.port", ["obs", "port"]),
        ("server.port", ["server", "port"]),
        ("auth.jwt_secret", ["auth", "jwt_secret"]),
        ("secrets_file", ["secrets_file"]),
    ]

    for label, pth in required_paths:
        if not has_path(cfg, pth):
            err(f"Chave obrigatória ausente em config.json: {label}")
            critical = True
        else:
            ok(f"Chave presente: {label}")

    if critical:
        err("config.json está incompleto. Corrija antes de prosseguir.")
        sys.exit(1)

    # 4) Valida tipos e valores
    # obs.port e server.port devem ser inteiros
    try:
        obs_port = int(cfg["obs"]["port"])
        ok(f"obs.port é inteiro: {obs_port}")
    except Exception:
        err("obs.port deve ser um número inteiro")
        critical = True

    try:
        server_port = int(cfg["server"]["port"])
        ok(f"server.port é inteiro: {server_port}")
    except Exception:
        err("server.port deve ser um número inteiro")
        critical = True

    # jwt_secret não pode ser placeholder óbvio
    jwt = cfg["auth"].get("jwt_secret", "")
    if not jwt or jwt.strip() == "" or "troque" in jwt.lower() or "secret" in jwt.lower():
        err("auth.jwt_secret parece inseguro ou é placeholder. Defina um JWT secret forte em config.json")
        critical = True
    else:
        ok("auth.jwt_secret parece definido")

    # 5) Verifica arquivo de secrets apontado
    secrets_file = cfg.get("secrets_file")
    if secrets_file:
        secrets_path = (ROOT / secrets_file) if not Path(secrets_file).is_absolute() else Path(secrets_file)
        if not secrets_path.exists():
            err(f"Arquivo de secrets não encontrado: {secrets_path}")
            critical = True
        else:
            ok(f"Arquivo de secrets encontrado: {secrets_path}")
    else:
        warn("Nenhum secrets_file configurado; se usar OAuth ou chaves, configure secrets_file em config.json")
        warnings.append("secrets_file não configurado")

    # 6) Analisa requirements.txt
    pkgs = read_requirements(REQS_PATH)
    if pkgs is None:
        err("Não foi possível ler requirements.txt")
        sys.exit(1)

    missing = ESSENTIAL_PKGS - pkgs
    if missing:
        err(f"Pacotes essenciais ausentes em requirements.txt: {', '.join(sorted(missing))}")
        critical = True
    else:
        ok("Pacotes essenciais presentes em requirements.txt")

    dev_found = DEV_PKGS & pkgs
    if dev_found:
        warn(f"Pacotes de desenvolvimento detectados em requirements.txt: {', '.join(sorted(dev_found))}")
        warnings.append("dev_packages_in_requirements")

    # Se config referencia youtube/oauth, verifique libs google
    uses_oauth = False
    yt_cfg = cfg.get("youtube") or cfg.get("youtube", {})
    if isinstance(yt_cfg, dict) and yt_cfg.get("client_secrets_path"):
        uses_oauth = True

    if uses_oauth:
        missing_oauth = OAUTH_PKGS - pkgs
        if missing_oauth:
            warn(f"Config.json referencia OAuth/YouTube mas faltam libs google em requirements.txt: {', '.join(sorted(missing_oauth))}")
            warnings.append("oauth_libs_missing")
        else:
            ok("Libs Google OAuth presentes em requirements.txt")

    # 7) Recomendações de sistema (não bloqueante)
    sys_reqs = []
    if "cryptography" in pkgs:
        sys_reqs.append("libssl-dev libffi-dev build-essential (already in Dockerfile)")

    if "obs-websocket-py" in pkgs:
        sys_reqs.append("obs-websocket server/plugin must be installed in OBS (external requirement)")

    if sys_reqs:
        print()
        warn("Recomendações de dependências de sistema / pré-requisitos (não bloqueante):")
        for r in sys_reqs:
            print("  - " + r)

    # 8) Resultado final
    print()
    if critical:
        err("Validação falhou: erros críticos detectados. Corrija e tente novamente.")
        sys.exit(1)

    if warnings:
        warn("Validação concluída com avisos. Verifique as mensagens acima.")
        # Retornamos 0 para permitir build, mas imprimimos aviso. Se preferir bloquear, mude para sys.exit(2)
        sys.exit(0)

    ok("Validação concluída sem problemas. Pronto para build.")
    sys.exit(0)


if __name__ == "__main__":
    main()
