"""Liga/desliga o launcher como autostart no Windows.

Usa o registro do Windows (HKEY_CURRENT_USER...Run) que e o jeito mais
robusto e nao depende de criar atalhos .lnk (que exigiriam pywin32).
"""

import sys

REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MediaAutomationServer"


def is_enabled() -> bool:
    """Retorna ``True`` se o autostart esta ativo no registro."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg  # type: ignore
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            except FileNotFoundError:
                return False
    except OSError:
        return False


def enable(executable_path: str) -> bool:
    """Adiciona o launcher ao autostart do usuario.

    Args:
        executable_path: Caminho absoluto do exe ou script a executar.

    Returns:
        ``True`` em sucesso.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg  # type: ignore
    except ImportError:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            quoted = f'"{executable_path}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, quoted)
        return True
    except OSError:
        return False


def disable() -> bool:
    """Remove o launcher do autostart."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg  # type: ignore
    except ImportError:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        return True
    except OSError:
        return False
