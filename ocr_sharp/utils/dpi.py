import ctypes

def set_dpi_awareness():
    try:
        # For Windows 8.1+
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            # For Windows Vista/7
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError) as e:
            print(f"[DPI WARNING] Could not set DPI awareness: {e}")
