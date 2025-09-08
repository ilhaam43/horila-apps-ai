"""budget/settings.py

This module is used to write settings contents related to budget app
"""

from horilla.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "budget.context_processors.default_currency",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "budget.context_processors.host",
)