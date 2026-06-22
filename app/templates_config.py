"""Configuração dos templates Jinja2 para o MezzaRPG Web."""
from pathlib import Path
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Ícones (emoji) por classe de personagem.
CLASS_ICONS = {
    "Bárbaro": "🪓",
    "Bardo": "🎭",
    "Bruxo": "🔮",
    "Clérigo": "⛪",
    "Druida": "🌿",
    "Feiticeiro": "✨",
    "Guerreiro": "⚔️",
    "Ladino": "🗡️",
    "Mago": "📜",
    "Monge": "🥋",
    "Paladino": "🛡️",
    "Patrulheiro": "🏹",
    "Artífice": "⚙️",
    "Aventureiro": "🗺️",
}


# Filtros personalizados
def class_icon_filter(classe: str) -> str:
    """Retorna o ícone (emoji) da classe de personagem informada."""
    return CLASS_ICONS.get(classe, "❓")


templates.env.filters["class_icon"] = class_icon_filter
