"""Servico de autenticacao: bootstrap do usuario padrao + validacao de credenciais."""

from app.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    """Operacoes de alto nivel para autenticacao de usuarios."""

    def __init__(self, user_repository: UserRepository | None = None) -> None:
        """Inicializa o servico com um repositorio opcional (DI-friendly).

        Args:
            user_repository: Repositorio injetado (default: novo ``UserRepository``).
        """
        self._users = user_repository or UserRepository()

    def ensure_default_user(self) -> None:
        """Cria o usuario padrao do .env caso nao exista nenhum cadastrado.

        Chamado uma unica vez no startup, garantindo que a aplicacao seja
        utilizavel imediatamente apos a primeira execucao.
        """
        if self._users.list_all():
            return
        settings = get_settings()
        user = User(
            username=settings.default_user,
            password_hash=hash_password(settings.default_password),
        )
        self._users.create(user)

    def authenticate(self, username: str, password: str) -> User | None:
        """Valida credenciais e retorna o usuario em caso de sucesso.

        Args:
            username: Username submetido.
            password: Senha em texto puro.

        Returns:
            ``User`` autenticado, ou ``None`` se invalido.
        """
        user = self._users.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
