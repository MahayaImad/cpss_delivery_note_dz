from . import models
# Import du hook simplifié seulement si le fichier existe
try:
    from .hooks import _post_init_hook
except ImportError:
    # Si pas de hook, on continue sans erreur
    pass
