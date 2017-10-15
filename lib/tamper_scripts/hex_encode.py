from builtins import str
from builtins import hex
from lib.core.settings import (
    logger,
    set_color
)


def tamper(payload, warning=True, **kwargs):
    if warning:
        logger.warning(set_color(
            "hex tamper scripts may increase the risk of false positives...", level=30
        ))
    retval = hex(hash(payload))
    if "-" in str(retval):
        return retval[1:-1]
    else:
        return retval
