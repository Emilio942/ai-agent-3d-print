"""Compatibility stub shim exposing printer support APIs at top level.

This module keeps legacy imports like ``import multi_printer_support`` working by
forwarding to the implementation that now lives under
``printer_support.multi_printer_support``.
"""

from printer_support.multi_printer_support import *  # noqa: F401,F403
