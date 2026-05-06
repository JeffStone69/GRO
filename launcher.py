#!/usr/bin/env python3
"""
XForge Trader Launcher v8.7 - Immediate splash screen + loading status popup for macOS Finder double-click.
Custom icon: Use SMI-LOGO.jpeg in Finder (right-click app -> Get Info -> Change icon).
"""
import tkinter as tk
import subprocess
import sys
import time
import os

def show_splash():
    root = tk.Tk()
    root.title("XForge Trader v8.7 Launcher")
    root.geometry("640x420")
    root.configure(bg="#0a0f1a")
    root.overrideredirect(True)  # No title bar for clean splash

    # Center on screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 640) // 2
    y = (screen_height - 420) // 2
    root.geometry(f"+{x}+{y}")

    # Logo / title
    title_label = tk.Label(root, text="XFORGE TRADER", font=("Helvetica", 36, "bold"), bg="#0a0f1a", fg="#22c55e")
    title_label.pack(pady=40)
    subtitle = tk.Label(root, text="v8.7 · Self-Improving Trading Workstation", font=("Helvetica", 14), bg="#0a0f1a", fg="#e0e7ff")
    subtitle.pack()

    # Status popup area
    status_frame = tk.Frame(root, bg="#111827", relief="sunken", bd=2)
    status_frame.pack(pady=30, padx=60, fill="x")
    status_label = tk.Label(status_frame, text="🚀 Initializing dependencies...", font=("Helvetica", 16), bg="#111827", fg="#22c55e")
    status_label.pack(pady=20)

    # Progress simulation
    def update_status():
        statuses = [
            "🚀 Initializing dependencies...",
            "📡 Loading real-time feeds...",
            "📊 Connecting watchlist & optimizer...",
            "🔄 Preparing Strategy Optimizer...",
            "✅ Launching Gradio interface..."
        ]
        for i, s in enumerate(statuses):
            status_label.config(text=s)
            root.update()
            time.sleep(0.6)
        root.destroy()

    root.after(100, update_status)
    root.mainloop()

if __name__ == "__main__":
    show_splash()
    # Launch main app
    script_path = os.path.join(os.path.dirname(__file__), "FORGE/xforge_trader.py")
    subprocess.Popen([sys.executable, script_path])
