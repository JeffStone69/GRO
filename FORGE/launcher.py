#!/usr/bin/env python3
"""
XForge Trader v7.4 Launcher
- Shows SIM_LOGO.jpeg splashscreen (falls back to text if missing)
- First-run prompt for Grok (xAI) API key
- Safely stores key in .env + os.environ
- Launches the main app
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def show_splash_and_launch():
    root = tk.Tk()
    root.title("XForge Trader v7.4 Launcher")
    root.geometry("420x320")
    root.configure(bg="#0a0a0a")

    # Splash with logo or text
    if HAS_PIL and os.path.exists("SIM_LOGO.jpeg"):
        try:
            img = Image.open("SIM_LOGO.jpeg")
            img = img.resize((380, 180), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(root, image=photo, bg="#0a0a0a")
            logo_label.image = photo
            logo_label.pack(pady=15)
        except Exception:
            pass
    else:
        logo_label = tk.Label(root, text="🚀 XFORGE TRADER v7.4\nTSLA • NVDA • Max History • Self-Improving",
                              font=("Arial", 16, "bold"), fg="#00ffcc", bg="#0a0a0a")
        logo_label.pack(pady=40)

    status = tk.Label(root, text="Initializing secure launcher...", fg="white", bg="#0a0a0a", font=("Arial", 10))
    status.pack(pady=5)

    def proceed():
        root.destroy()
        # Check / prompt for Grok API key
        if not os.getenv("GROK_API_KEY"):
            key_window = tk.Tk()
            key_window.title("First Run - Grok API Key")
            key_window.geometry("450x200")
            key_window.configure(bg="#111")

            tk.Label(key_window, text="Enter your Grok (xAI) API Key\n(Starts with 'xai-')", 
                     fg="#00ffcc", bg="#111", font=("Arial", 12)).pack(pady=15)
            
            key_entry = tk.Entry(key_window, width=55, show="*", font=("Arial", 11))
            key_entry.pack(pady=5)

            def save_and_launch():
                key = key_entry.get().strip()
                if not key:
                    messagebox.showerror("Error", "API key is required!")
                    return
                os.environ["GROK_API_KEY"] = key
                # Safely persist (append to .env)
                try:
                    with open(".env", "a") as f:
                        f.write(f"\nGROK_API_KEY={key}\n")
                except Exception:
                    pass
                messagebox.showinfo("Success", "Grok API key saved securely.\nLaunching XForge Trader...")
                key_window.destroy()
                # Launch main app
                subprocess.Popen([sys.executable, "xforge_trader_v74.py"])
                sys.exit(0)

            tk.Button(key_window, text="Save Key & Launch App", command=save_and_launch,
                      bg="#00cc66", fg="white", font=("Arial", 11, "bold")).pack(pady=15)
            key_window.mainloop()
        else:
            # Key already set → launch immediately
            subprocess.Popen([sys.executable, "xforge_trader_v74.py"])
            sys.exit(0)

    root.after(2200, proceed)  # Splash duration
    root.mainloop()

if __name__ == "__main__":
    show_splash_and_launch()
