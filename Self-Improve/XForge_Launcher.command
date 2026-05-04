#!/bin/bash

# ============================================================
# XForge Self-Improvement - macOS Single-File Launcher (FIXED)
# Futuristic Splash using SMI-LOGO.jpeg + Secure First-Run
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

clear
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    X F O R G E                               ║"
echo "║              Self-Improvement Module                         ║"
echo "║                   macOS Launcher                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Preparing first-run experience..."
echo ""

# Quick file checks
if [ ! -f "SIM.py" ]; then
    echo "❌ SIM.py not found in this folder."
    read -n 1 -s -r -p "Press any key to exit..."
    exit 1
fi

if [ ! -f "SMI-LOGO.jpeg" ]; then
    echo "❌ SMI-LOGO.jpeg not found. Download it from the repo first."
    read -n 1 -s -r -p "Press any key to exit..."
    exit 1
fi

# Create the bundled Python launcher (self-contained)
cat > /tmp/xforge_launcher.py << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
XForge macOS Launcher - Bundled Edition (FIXED PATHS)
Futuristic splash using SMI-LOGO.jpeg
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# FIX: Always use the current working directory (set by the .command file)
SCRIPT_DIR = os.getcwd()

# ==================== FUTURISTIC SPLASH WITH LOGO ====================
def show_splash_with_logo():
    splash = tk.Tk()
    splash.title("XFORGE")
    splash.attributes("-fullscreen", True)
    splash.configure(bg="#0a0f1a")
    
    frame = tk.Frame(splash, bg="#0a0f1a")
    frame.place(relx=0.5, rely=0.5, anchor="center")
    
    # Load and display your logo
    try:
        logo_path = os.path.join(SCRIPT_DIR, "SMI-LOGO.jpeg")
        img = Image.open(logo_path)
        img = img.resize((600, 600), Image.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)
        
        logo_label = tk.Label(frame, image=logo_img, bg="#0a0f1a")
        logo_label.image = logo_img
        logo_label.pack(pady=10)
    except Exception:
        title = tk.Label(frame, text="XFORGE", font=("Helvetica", 72, "bold"), 
                         fg="#22c55e", bg="#0a0f1a")
        title.pack(pady=20)
    
    subtitle = tk.Label(frame, text="SELF-IMPROVEMENT MODULE", 
                        font=("Helvetica", 20, "normal"), 
                        fg="#64748b", bg="#0a0f1a")
    subtitle.pack(pady=8)
    
    progress = ttk.Progressbar(frame, length=500, mode='indeterminate', 
                               style="TProgressbar")
    progress.pack(pady=30)
    progress.start(12)
    
    status = tk.Label(frame, text="Initializing Secure Environment...", 
                      font=("Helvetica", 13), fg="#94a3b8", bg="#0a0f1a")
    status.pack(pady=15)
    
    def close_splash():
        progress.stop()
        splash.destroy()
    
    splash.after(2800, close_splash)
    splash.mainloop()

# ==================== API KEY WINDOW ====================
def get_api_key():
    key_window = tk.Tk()
    key_window.title("XForge • Secure API Access")
    key_window.configure(bg="#0a0f1a")
    key_window.geometry("560x400")
    key_window.resizable(False, False)
    key_window.eval('tk::PlaceWindow . center')
    
    main_frame = tk.Frame(key_window, bg="#0a0f1a", padx=50, pady=40)
    main_frame.pack(expand=True, fill="both")
    
    header = tk.Label(main_frame, text="🔐 API KEY REQUIRED", 
                      font=("Helvetica", 22, "bold"), fg="#22c55e", bg="#0a0f1a")
    header.pack(pady=(0, 25))
    
    desc = tk.Label(main_frame, text="Enter your xAI Grok API key.\nIt will be used only for this session (never saved).", 
                    font=("Helvetica", 13), fg="#94a3b8", bg="#0a0f1a", justify="center")
    desc.pack(pady=(0, 30))
    
    key_var = tk.StringVar()
    key_entry = tk.Entry(main_frame, textvariable=key_var, show="•", 
                         font=("Helvetica", 18), bg="#1e2937", fg="#e0e7ff",
                         insertbackground="#22c55e", relief="flat", bd=3)
    key_entry.pack(pady=10, ipady=14, fill="x")
    key_entry.focus_set()
    
    status_label = tk.Label(main_frame, text="", font=("Helvetica", 12), 
                            fg="#ef4444", bg="#0a0f1a")
    status_label.pack(pady=15)
    
    button_frame = tk.Frame(main_frame, bg="#0a0f1a")
    button_frame.pack(pady=25)
    
    def validate_and_continue():
        key = key_var.get().strip()
        if not key:
            status_label.config(text="❌ Please enter a valid xAI API key", fg="#ef4444")
            return
        try:
            import openai
            client = openai.OpenAI(api_key=key, base_url="https://api.x.ai/v1")
            client.chat.completions.create(model="grok-4.3", messages=[{"role": "user", "content": "test"}], max_tokens=5)
            os.environ["XAI_API_KEY"] = key
            status_label.config(text="✅ Key validated! Launching...", fg="#22c55e")
            key_window.after(900, key_window.destroy)
        except Exception as e:
            status_label.config(text=f"❌ Invalid key: {str(e)[:70]}", fg="#ef4444")
    
    def use_env():
        env_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        if env_key:
            os.environ["XAI_API_KEY"] = env_key
            key_window.destroy()
        else:
            status_label.config(text="❌ No environment key found.", fg="#ef4444")
    
    validate_btn = tk.Button(button_frame, text="✅ VALIDATE & CONTINUE", 
                             command=validate_and_continue, 
                             font=("Helvetica", 14, "bold"), bg="#22c55e", fg="white",
                             padx=35, pady=14, relief="flat")
    validate_btn.pack(side="left", padx=20)
    
    env_btn = tk.Button(button_frame, text="🔑 USE ENV KEY", 
                        command=use_env, 
                        font=("Helvetica", 13), bg="#334155", fg="#e0e7ff",
                        padx=25, pady=14, relief="flat")
    env_btn.pack(side="left", padx=20)
    
    key_window.mainloop()
    return os.getenv("XAI_API_KEY")

# ==================== INSTALL & LAUNCH ====================
def install_dependencies():
    print("\n🔧 Installing dependencies...")
    packages = ["openai", "pandas", "pydantic", "gradio", "requests", "pillow"]
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"   ✓ {pkg}")
        except ImportError:
            print(f"   Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
    print("✅ All dependencies ready.\n")

def launch_sim():
    print("🚀 Launching XForge Self-Improvement UI...")
    time.sleep(0.8)
    sim_path = os.path.join(SCRIPT_DIR, "SIM.py")   # Now correctly points to your folder
    subprocess.Popen([sys.executable, sim_path])
    print("✅ XForge is now running at http://127.0.0.1:7860")
    print("   You can close this window when done.")

# ==================== MAIN FLOW ====================
if __name__ == "__main__":
    show_splash_with_logo()
    
    existing_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not existing_key:
        print("🔐 No API key detected. Opening secure input window...")
        key = get_api_key()
        if not key:
            print("❌ No API key provided. Exiting.")
            sys.exit(0)
    else:
        print("🔑 Using API key from environment.")
    
    install_dependencies()
    launch_sim()
    
    print("\n✨ XForge Launcher complete. Enjoy your session!")
    input("Press Enter to close this window...")
PYTHON_EOF

# Run the fixed bundled launcher
python3 /tmp/xforge_launcher.py

echo ""
echo "✅ XForge session finished."
read -n 1 -s -r -p "Press any key to close this Terminal window..."
