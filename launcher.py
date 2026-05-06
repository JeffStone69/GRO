#!/usr/bin/env python3
"""
XForge Trader Launcher v9.2 Beta – Final
- Interactive menu: Update or Run
- Silent terminal on choice 2
- LOGO-SIM.jpeg splash
- Full logging
"""

import tkinter as tk
from tkinter import PhotoImage
import subprocess
import sys
import time
import os
import logging
from pathlib import Path

log_file = Path(__file__).parent / "XForge_Beta.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(log_file, mode="a"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("XForgeLauncher")

def get_screen_info():
    root = tk.Tk()
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.destroy()
    return w, h

def show_splash():
    splash = tk.Tk()
    splash.title("XForge Trader v9.2 Beta")
    splash.configure(bg="#0a0f1a")
    splash.overrideredirect(True)

    screen_w, screen_h = get_screen_info()
    splash_w = min(max(900, int(screen_w * 0.48)), 1300)
    splash_h = min(max(580, int(screen_h * 0.48)), 850)
    splash.geometry(f"{splash_w}x{splash_h}")
    x = (screen_w - splash_w) // 2
    y = (screen_h - splash_h) // 2
    splash.geometry(f"+{x}+{y}")

    logo_path = Path(__file__).parent / "LOGO-SIM.jpeg"
    if logo_path.exists():
        try:
            logo = PhotoImage(file=str(logo_path))
            tk.Label(splash, image=logo, bg="#0a0f1a").pack(pady=25)
        except Exception:
            tk.Label(splash, text="XFORGE TRADER", font=("Helvetica", 52, "bold"), bg="#0a0f1a", fg="#22c55e").pack(pady=30)
    else:
        tk.Label(splash, text="XFORGE TRADER", font=("Helvetica", 52, "bold"), bg="#0a0f1a", fg="#22c55e").pack(pady=30)

    tk.Label(splash, text="v9.2 Beta • Self-Improving Autonomous Trading Intelligence",
             font=("Helvetica", 18, "italic"), bg="#0a0f1a", fg="#a5b4fc").pack(pady=10)

    status_frame = tk.Frame(splash, bg="#111827", relief="sunken", bd=4)
    status_frame.pack(pady=25, padx=80, fill="x")
    status_label = tk.Label(status_frame, text="Initializing secure environment...",
                            font=("Helvetica", 18, "bold"), bg="#111827", fg="#22c55e")
    status_label.pack(pady=35)

    def update_progress():
        messages = ["Loading LOGO-SIM...", "Preparing environment...", "Launching XForge..."]
        for msg in messages:
            status_label.config(text=msg)
            splash.update()
            time.sleep(0.7)
            logger.info(msg)
        splash.destroy()

    splash.after(200, update_progress)
    splash.mainloop()

def launch_with_choice():
    print("\nXForge Trader v9.2 Beta – Choose Option:")
    print("1. Update everything (fresh venv + reinstall dependencies + reset databases)")
    print("2. Run final XForge Trader (fast launch – recommended)")
    choice = input("Enter choice [1/2]: ").strip()

    script_dir = Path(__file__).parent
    main_script = script_dir / "FORGE" / "xforge_trader.py"

    if choice == "1":
        logger.info("User chose UPDATE mode")
        update_cmd = [sys.executable, "-m", "pip", "install", "-r", str(script_dir / "FORGE" / "requirements.txt")]
        subprocess.run(update_cmd)
        print("Update complete. Now running the app...")
        choice = "2"

    if choice == "2":
        os.environ["XFORGE_FULLSCREEN"] = "true"
        os.environ["XFORGE_LARGE_TEXT"] = "true"
        os.environ["XFORGE_BETA"] = "true"

        cmd = [sys.executable, str(main_script)]
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            subprocess.Popen(cmd, startupinfo=startupinfo, creationflags=creationflags)
            logger.info("XForge Trader v9.2 Beta launched silently in new browser window.")
        except Exception as e:
            logger.error(f"Launch failed: {e}")
            sys.exit(1)
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("=== XForge Trader v9.2 Beta Launch Started ===")
    show_splash()
    launch_with_choice()
