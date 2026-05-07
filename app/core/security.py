"""Hash de senhas (bcrypt) e tokens JWT.

Usamos a biblioteca ``bcrypt`` diretamente (sem ``passlib``), porque ``passlib``
nao recebe atualizacoes ha anos e quebra com versoes recentes de ``bcrypt``.
Manter as primitivas isoladas neste modulo significa que trocar bcrypt por
argon2 no futuro exige mudar apenas este arquivo.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings


# Limite imposto pelo proprio bcrypt: senhas com mais de 72 bytes sao recusadas.
_BCRYPT_MAX_BYTES = 72


def _truncate_to_bcrypt_limit(plain_password: str) -> bytes:
    """Codifica a senha em UTF-8 truncando ao limite de 72 bytes do bcrypt.

    O truncamento e feito em bytes (nao caracteres) para nao quebrar
    sequencias multibyte UTF-8 no meio.

    Args:
        plain_password: Senha em texto puro.

    Returns:
        Bytes UTF-8 prontos para o bcrypt (no maximo 72 bytes).
    """
    encoded = plain_password.encode("utf-8")
    if len(encoded) <= _BCRYPT_MAX_BYTES:
        return encoded
    # Trunca byte a byte ate cair em uma fronteira de caractere valida.
    truncated = encoded[:_BCRYPT_MAX_BYTES]
    while truncated:
        try:
            truncated.decode("utf-8")
            break
        except UnicodeDecodeError:
            truncated = truncated[:-1]
    return truncated


def hash_password(plain_password: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro.

    Args:
        plain_password: Senha em texto puro.

    Returns:
        Hash bcrypt como string UTF-8.
    """
    encoded = _truncate_to_bcrypt_limit(plain_password)
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Valida uma senha em texto puro contra um hash bcrypt armazenado.

    Args:
        plain_password: Senha em texto puro recebida do cliente.
        password_hash: Hash bcrypt armazenado no banco.

    Returns:
        ``True`` se a senha corresponde ao hash; ``False`` caso contrario
        (incluindo casos de hash malformado).
    """
    encoded = _truncate_to_bcrypt_limit(plain_password)
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Gera um JWT de acesso assinado com a chave da aplicacao.

    Args:
        subject: ``sub`` do token, geralmente o username.
        extra_claims: Claims adicionais opcionais a serem mescladas no payload.

    Returns:
        Token JWT codificado.
    """
    settings = get_settings()
    expire_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire_at}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica e valida um JWT.

    Args:
        token: Token JWT codificado.

    Returns:
        Payload decodificado se valido; ``None`` se invalido ou expirado.
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
