"""Compatibility stub for the relocated printer emulator module."""

from printer_support.printer_emulator import (  # noqa: F401
    EmulatedPrinterType,
    PrinterEmulator,
    PrinterEmulatorManager,
)

__all__ = [
    "EmulatedPrinterType",
    "PrinterEmulator",
    "PrinterEmulatorManager",
]