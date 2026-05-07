"""Rotas de paginas HTML (desktop, mobile e login)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.dependencies import get_current_user_optional
from app.services.network_service import NetworkService


router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")

# Workaround: desabilita o cache interno do Jinja2.
# Python 3.14 (pre-release) causa um TypeError no cache LRU do Jinja2
# ("cannot use 'tuple' as a dict key"). Para o tamanho deste app, o
# impacto de re-parsear templates a cada request e desprezivel.
templates.env.cache = None


def _network_info() -> dict:
    """Helper que retorna info de rede para injetar nos templates.

    Returns:
        Dicionario com ip, hostname, port, desktop_url, mobile_url.
    """
    return NetworkService().get_info()


@router.get("/", response_class=HTMLResponse)
def desktop_home(
    request: Request,
    username: str | None = Depends(get_current_user_optional),
) -> HTMLResponse:
    """Renderiza o painel completo (desktop) ou redireciona para o login.

    A info de rede e calculada server-side e injetada no template para que
    a URL mobile apareca imediatamente, sem depender de JS.

    Args:
        request: Request atual.
        username: Username do usuario autenticado, se houver.

    Returns:
        Resposta HTML do painel ou redirect para ``/login``.
    """
    if not username:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        request=request,
        name="desktop.html",
        context={"username": username, "network": _network_info()},
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    """Renderiza a tela de login.

    Args:
        request: Request atual.

    Returns:
        Resposta HTML do formulario de login.
    """
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@router.get("/mobile", response_class=HTMLResponse)
def mobile_home(
    request: Request,
    username: str | None = Depends(get_current_user_optional),
) -> HTMLResponse:
    """Renderiza o painel mobile, ou redireciona para o login.

    Pre-carrega tipos de culto e info de rede via SSR pra que o app
    funcione mesmo se houver problema com fetch JS no celular.

    Args:
        request: Request atual.
        username: Username autenticado, se houver.

    Returns:
        Resposta HTML do controle mobile ou redirect.
    """
    if not username:
        return RedirectResponse(url="/login?next=/mobile")

    # Mobile nao usa mais ``service_types`` (a aba Live foi removida do
    # celular). Mantemos network pra exibir info de rede e qr code se
    # precisar no futuro.
    return templates.TemplateResponse(
        request=request,
        name="mobile.html",
        context={
            "username": username,
            "network": _network_info(),
        },
    )
