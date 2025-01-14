import logging
import sys

from ws_sdk.web import WS
from ws_sdk.client import WSClient

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

__all__ = (
    "WS",
    "WSClient",
    "ws_constants",
    "ws_utilities"
)
