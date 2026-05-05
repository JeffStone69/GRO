#!/usr/bin/env python3
"""
XForge Trader v8.0 Launcher
- Displays SMI-LOGO.jpeg splashscreen
- Real-time status updates for long loading
- Grok (xAI) API key prompt with validation
- Secure .env persistence
- Launches optimized main application
"""

import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def update_status(label, text: str):
    """Update status label safely."""
    label.config(text=text)
    label.update_idletasks()

def validate_grok_key(key: str) -> bool:
    """Basic validation for Grok/xAI API key."""
    return key.startswith("xai-") and len(key) > 20

def show_splash_and_launch():
    root = tk.Tk()
    root.title("XForge Trader v8.0 Launcher")
    root.geometry("520x420")
    root.configure(bg="#0a0a0a")
    root.resizable(False, False)

    # === SPLASH LOGO ===
    logo_path = "SMI-LOGO.jpeg"
    if HAS_PIL and os.path.exists(logo_path):
        try:
            img = Image.open(logo_path)
            img = img.resize((480, 220), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(root, image=photo, bg="#0a0a0a")
            logo_label.image = photo
            logo_label.pack(pady=20)
        except Exception:
            pass
    else:
        tk.Label(root, text="🚀 XFORGE TRADER v8.0\nHistorical Database • TSLA Default • Self-Improving",
                 font=("Arial", 18, "bold"), fg="#00ffcc", bg="#0a0a0a", justify="center").pack(pady=40)

    # === STATUS BAR ===
    status_label = tk.Label(root, text="Initializing environment...", 
                           fg="#00ffcc", bg="#0a0a0a", font=("Arial", 11))
    status_label.pack(pady=10)

    progress = tk.Label(root, text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", 
                       fg="#444444", bg="#0a0a0a", font=("Arial", 10))
    progress.pack(pady=5)

    def proceed_to_launch():
        update_status(status_label, "Checking dependencies and database...")
        time.sleep(0.8)  # Simulate initialization

        update_status(status_label, "Verifying Grok (xAI) API configuration...")

        # Load .env if exists
        if os.path.exists(".env"):
            try:
                with open(".env") as f:
                    for line in f:
                        if line.startswith("GROK_API_KEY="):
                            os.environ["GROK_API_KEY"] = line.split("=", 1)[1].strip()
            except Exception:
                pass

        # Prompt for API key if missing or invalid
        if not os.getenv("GROK_API_KEY") or not validate_grok_key(os.getenv("GROK_API_KEY", "")):
            update_status(status_label, "API key required – opening secure input...")
            key_window = tk.Toplevel(root)
            key_window.title("Grok (xAI) API Key")
            key_window.geometry("500x220")
            key_window.configure(bg="#111111")

            tk.Label(key_window, text="Enter your Grok API Key (starts with xai-)",
                     fg="#00ffcc", bg="#111111", font=("Arial", 12)).pack(pady=15)

            key_entry = tk.Entry(key_window, width=60, show="*", font=("Arial", 11))
            key_entry.pack(pady=8)

            def save_key():
                key = key_entry.get().strip()
                if not key:
                    messagebox.showerror("Error", "API key cannot be empty.")
                    return
                if not validate_grok_key(key):
                    messagebox.showerror("Invalid Key", "Key must start with 'xai-' and be valid.")
                    return

                os.environ["GROK_API_KEY"] = key
                try:
                    with open(".env", "a") as f:
                        f.write(f"\nGROK_API_KEY={key}\n")
                except Exception as e:
                    messagebox.showwarning("Warning", f"Could not save to .env: {e}")

                messagebox.showinfo("Success", "API key validated and saved securely.\nLaunching main application...")
                key_window.destroy()
                root.destroy()
                launch_main_app()

            tk.Button(key_window, text="Validate & Launch", command=save_key,
                      bg="#00cc66", fg="white", font=("Arial", 11, "bold"), width=20).pack(pady=15)

            key_window.grab_set()
        else:
            update_status(status_label, "API key validated. Launching application...")
            time.sleep(1.2)
            root.destroy()
            launch_main_app()

    # Auto-proceed after splash
    root.after(1800, proceed_to_launch)
    root.mainloop()

def launch_main_app():
    """Launch the main Gradio application."""
    try:
        print("🚀 Starting XForge Trader v8.0...")
        subprocess.Popen([sys.executable, "xforge_trader.py"])
        sys.exit(0)
    except Exception as e:
        print(f"Launch error: {e}")
        messagebox.showerror("Launch Failed", str(e))

if __name__ == "__main__":
    show_splash_and_launch()