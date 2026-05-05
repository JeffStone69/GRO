#!/usr/bin/env python3
"""
XForge Trader v8.0 Launcher
- Splash screen with logo
- Grok (xAI) API key prompt on first run
- Launches main app
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def show_splash_and_launch():
    root = tk.Tk()
    root.title("XForge Trader v8.0")
    root.geometry("460x340")
    root.configure(bg="#0a0a0a")

    if HAS_PIL and os.path.exists("SMI-LOGO.jpeg"):
        try:
            img = Image.open("SMI-LOGO.jpeg")
            img = img.resize((400, 180), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=photo, bg="#0a0a0a")
            label.image = photo
            label.pack(pady=20)
        except:
            pass
    else:
        tk.Label(root, text="🚀 XFORGE TRADER v8.0\nGrok-Powered • TSLA Focused", 
                 font=("Arial", 18, "bold"), fg="#00ffcc", bg="#0a0a0a").pack(pady=60)

    status = tk.Label(root, text="Initializing...", fg="white", bg="#0a0a0a", font=("Arial", 10))
    status.pack(pady=10)

    def proceed():
        root.destroy()
        # Grok API Key handling
        if not os.getenv("GROK_API_KEY"):
            key_win = tk.Tk()
            key_win.title("xAI Grok API Key Required")
            key_win.geometry("500x220")
            key_win.configure(bg="#111111")

            tk.Label(key_win, text="Enter your xAI Grok API Key\n(starts with gsk_ or xai-)", 
                     fg="#00ffcc", bg="#111111", font=("Arial", 12)).pack(pady=20)
            
            entry = tk.Entry(key_win, width=60, show="*", font=("Arial", 11))
            entry.pack(pady=5)

            def save_key():
                key = entry.get().strip()
                if not key:
                    messagebox.showerror("Error", "API key is required!")
                    return
                os.environ["GROK_API_KEY"] = key
                try:
                    with open(".env", "a") as f:
                        f.write(f"GROK_API_KEY={key}\n")
                except:
                    pass
                messagebox.showinfo("Success", "Key saved! Launching main application...")
                key_win.destroy()
                subprocess.Popen([sys.executable, "xforge_trader.py"])
                sys.exit(0)

            tk.Button(key_win, text="Save Key & Launch", command=save_key, 
                      bg="#00cc66", fg="white", font=("Arial", 11, "bold")).pack(pady=15)
            key_win.mainloop()
        else:
            subprocess.Popen([sys.executable, "xforge_trader.py"])
            sys.exit(0)

    root.after(1800, proceed)
    root.mainloop()

if __name__ == "__main__":
    show_splash_and_launch()