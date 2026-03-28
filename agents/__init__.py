"""
DJ/Producer Mentor Agents
Individual agent configurations and prompts
"""

from . import ar
from . import coach
from . import produtor
from . import curador
from . import estratega
from . import booker
from . import manager
from . import advogado

__all__ = [
    'ar',
    'coach',
    'produtor',
    'curador',
    'estratega',
    'booker',
    'manager',
    'advogado'
]

# Agent registry for easy access
AGENTS = {
    'ar': ar.AGENT_CONFIG,
    'coach': coach.AGENT_CONFIG,
    'produtor': produtor.AGENT_CONFIG,
    'curador': curador.AGENT_CONFIG,
    'estratega': estratega.AGENT_CONFIG,
    'booker': booker.AGENT_CONFIG,
    'manager': manager.AGENT_CONFIG,
    'advogado': advogado.AGENT_CONFIG,
}
