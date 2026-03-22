#!/bin/bash

cat << "EOF"
============================================================
   Ubuntu 24.04 Generic OCR Infrastructure Audit Report
============================================================
EOF

# 出力ファイル設定
REPORT="system_audit_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -i "$REPORT")
exec 2>&1

echo "--- [1-3] OS & Kernel ---"
lsb_release -a
uname -a
uptime

echo -e "\n--- [4-8] Display & Session (Wayland/X11 Check) ---"
echo "Session Type: $XDG_SESSION_TYPE"
echo "Display Env: $DISPLAY"
echo "Wayland Display: $WAYLAND_DISPLAY"
loginctl show-session $(loginctl | grep $(whoami) | awk '{print $1}') -p Type
xrandr --listmonitors 2>/dev/null || echo "xrandr not available (Standard in Wayland)"

echo -e "\n--- [9-10] .NET Environment ---"
dotnet --list-sdks
dotnet --list-runtimes

echo -e "\n--- [11-13] System Python ---"
python3 --version
which python3
pip3 --version 2>/dev/null || echo "pip3 not installed"

echo -e "\n--- [14] Essential Tool Check (Clipboard/Capture) ---"
dpkg -l | grep -E "xclip|wl-clipboard|gnome-screenshot|scrot|imagemagick" | awk '{print $2, $3}'

echo -e "\n--- [15-17] Project & VirtualEnv (Python) ---"
PROJECT_DIR="$HOME/projects/ver2.0_CSharp_Python_OCRClipboard"
VENV_DIR="$PROJECT_DIR/.venv-ocr27"
ls -ld "$PROJECT_DIR"
if [ -d "$VENV_DIR" ]; then
    echo "Venv Python Path: $(ls -l $VENV_DIR/bin/python)"
    $VENV_DIR/bin/pip list | grep -E "paddle|opencv|yomitoku|numpy|Pillow"
else
    echo "⚠️ VirtualEnv NOT FOUND at $VENV_DIR"
fi

echo -e "\n--- [18-22] Hardware & Resources ---"
ldd --version | head -n 1
groups
df -h . | awk 'NR==2 {print "Disk Space: " $4 " available"}'
free -h
cat /proc/cpuinfo | grep "model name" | head -n 1

echo -e "\n--- [23-24] GPU & Graphics ---"
lsmod | grep -E "nvidia|amdgpu|i915" | head -n 5
glxinfo | grep "OpenGL version" 2>/dev/null || echo "glxinfo not found"

echo -e "\n--- [25-26] Environment & C# Project Metadata ---"
env | grep -E "OCR_|PATH" | head -n 10
find "$PROJECT_DIR" -name "*.csproj" -exec grep -H "TargetFramework" {} \;

echo -e "\n--- [27-28] Network State (Simulation Context) ---"
ip addr | grep -E "inet " | grep -v "127.0.0.1"
nmcli device status 2>/dev/null || echo "nmcli not available"

echo -e "\n--- [29-30] Running Processes & System Logs ---"
ps aux | grep -E "python|dotnet|ocr_worker" | grep -v grep | head -n 5
journalctl -p 3 -xb | tail -n 10

echo -e "\n--- [31-34] Specific Library Verification ---"
$VENV_DIR/bin/python -c "import cv2; print('OpenCV Version:', cv2.__version__)" 2>/dev/null || echo "CV2 missing"
$VENV_DIR/bin/python -c "import PIL; print('Pillow Version:', PIL.PILLOW_VERSION if hasattr(PIL, 'PILLOW_VERSION') else PIL.__version__)" 2>/dev/null || echo "Pillow missing"
ls -l /dev/shm | head -n 5
which xclip && which wl-copy

echo -e "\n--- [35-40] Project Health & Filesystem ---"
ls -la /tmp/.X11-unix/
echo "Current Shell: $SHELL"
locale | grep LANG
[ -f "$PROJECT_DIR/ver2.0_C#+Python_OCRClipboard.sln" ] && echo "Solution file exists."
cd "$PROJECT_DIR" && tree -L 2

echo -e "\n============================================================"
echo "Audit Complete. Report saved to: $REPORT"
echo "============================================================"
