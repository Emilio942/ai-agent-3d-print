# Printer Support Module

This directory contains all printer-related support modules for the AI Agent 3D Print System.

## Contents

- `multi_printer_support.py` - Multi-printer detection and management system
- `enhanced_printer_agent.py` - Enhanced printer agent with advanced features
- Additional printer firmware support modules

## Features

- **Multi-Printer Detection**: Automatic discovery of connected 3D printers
- **Firmware Support**: Marlin, Prusa, Klipper, Ender, and generic printers
- **Connection Management**: Connect, disconnect, and monitor printer status
- **Hardware Communication**: Serial communication with printer hardware

## Usage

```python
from printer_support.multi_printer_support import MultiPrinterDetector

detector = MultiPrinterDetector()
printers = await detector.scan_for_printers()
```
