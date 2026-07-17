"""
conftest.py
-----------
Ajoute la racine du projet a sys.path pour permettre l'import des modules
utils/ et scripts/ depuis les tests, comme le font deja les scripts entre eux.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Les scripts appellent setup_logging() au niveau module (import), ce qui
# enveloppe sys.stdout.buffer dans un TextIOWrapper. Ca entre en conflit avec
# la capture de sortie de pytest a la fin de session. On neutralise l'appel
# avant que les scripts testes ne soient importes.
import utils.logging_utils  # noqa: E402

utils.logging_utils.setup_logging = lambda *args, **kwargs: None
