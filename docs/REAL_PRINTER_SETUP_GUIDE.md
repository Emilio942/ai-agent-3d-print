# 🖨️ Real 3D Printer Integration Guide

## Step 1: Hardware Detection

First, let's detect what serial ports and potential 3D printers are available on your system.

### Check Available Serial Ports

```bash
# List all serial devices
ls -la /dev/tty* | grep -E "(USB|ACM)"

# Check for common 3D printer devices
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "No USB/ACM devices found"

# Use dmesg to see recently connected devices
dmesg | tail -20 | grep -i usb
```

### Check USB Devices

```bash
# List USB devices (look for Arduino, CH340, FTDI, etc.)
lsusb | grep -iE "(arduino|ch340|ftdi|cp210|usb.*serial)"
```

## Step 2: Configure for Real Printer

### Update Configuration

Edit `config/settings.yaml`:

```yaml
printer:
  enabled: true
  mock_mode: false  # ← Change this to false
  serial:
    port: "/dev/ttyUSB0"  # ← Update to your actual port
    baudrate: 115200      # ← Adjust if needed (common: 115200, 250000)
    timeout: 10
    reconnect_attempts: 3
```

### Common Printer Ports:
- **Linux:** `/dev/ttyUSB0`, `/dev/ttyACM0`
- **macOS:** `/dev/cu.usbserial-*`, `/dev/cu.usbmodem*`
- **Windows:** `COM3`, `COM4`, etc.

### Common Baud Rates:
- **115200** (most common)
- **250000** (faster communication)
- **57600** (older printers)

## Step 3: Test Real Printer Connection

### Method 1: Auto-Detection
```bash
python main.py --detect-printers
```

### Method 2: Manual Connection Test
```bash
# Start system in real printer mode
python main.py --web --printer-port /dev/ttyUSB0

# Or with custom baud rate
python main.py --web --printer-port /dev/ttyUSB0 --baudrate 250000
```

### Method 3: API Testing
```bash
# Test printer detection
curl -X GET "http://127.0.0.1:8001/api/printers/detect"

# Test printer connection
curl -X POST "http://127.0.0.1:8001/api/printers/connect" \
  -H "Content-Type: application/json" \
  -d '{"port": "/dev/ttyUSB0", "baudrate": 115200}'

# Test basic commands
curl -X POST "http://127.0.0.1:8001/api/printers/command" \
  -H "Content-Type: application/json" \
  -d '{"command": "M115"}'  # Get firmware info
```

## Step 4: Verify Real Printer Functionality

### Basic G-code Commands to Test:

1. **Get Firmware Info:** `M115`
2. **Get Temperature:** `M105`
3. **Home All Axes:** `G28` (⚠️ Make sure printer is safe to home)
4. **Get Position:** `M114`
5. **Set Hotend Temp:** `M104 S180` (⚠️ Use appropriate temperature)

### Safety Checklist Before Testing:

- [ ] Printer is powered on and properly connected
- [ ] Print bed is clear of objects
- [ ] Filament is loaded (for temperature tests)
- [ ] Emergency stop is accessible
- [ ] Printer is in a safe location for homing movements

## Step 5: Full Workflow Test with Real Printer

Once basic connection is verified:

```bash
# Submit a simple print job
curl -X POST "http://127.0.0.1:8001/api/print-request" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a simple 1cm test cube",
    "priority": "normal"
  }'
```

## Troubleshooting

### Common Issues:

1. **Permission Denied:**
   ```bash
   sudo usermod -a -G dialout $USER
   # Then logout/login or reboot
   ```

2. **Port Already in Use:**
   ```bash
   sudo lsof /dev/ttyUSB0  # Check what's using the port
   sudo pkill -f "serial\|printer"  # Kill conflicting processes
   ```

3. **Wrong Baud Rate:**
   - Try 115200, 250000, or 57600
   - Check your printer's firmware documentation

4. **Hardware Issues:**
   ```bash
   # Test direct serial communication
   sudo apt install minicom
   minicom -D /dev/ttyUSB0 -b 115200
   ```

## Expected Results

### Successful Real Printer Connection:
- ✅ Printer detected in port scan
- ✅ Serial connection established
- ✅ Firmware info retrieved (M115)
- ✅ Temperature readings available (M105)
- ✅ Position queries working (M114)
- ✅ Basic movement commands accepted

### Integration Verification:
- ✅ Web interface shows "Connected" status
- ✅ Real-time temperature updates
- ✅ Print job submission works
- ✅ G-code streaming functional
- ✅ Pause/resume/stop controls work

---

**Next:** Run the detection commands to identify your 3D printer setup!
