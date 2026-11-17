"""Bad example: logging secrets."""

import logging

logger = logging.getLogger(__name__)


def authenticate(username: str, password: str) -> None:
    logger.info("Authenticating username=%s password=%s", username, password)


# Problem:
# Never log passwords, tokens, API keys, private keys, or secret-bearing headers.
