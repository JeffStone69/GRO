#!/usr/bin/env python3
"""
XForge Launcher - Futuristic Tech Edition
- Beautiful dark cyber splash screen
- Secure API key input (memory only)
- Auto-installs all dependencies
- Launches the premium SIM.py UI
"""

import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# ==================== FUTURISTIC SPLASH SCREEN ====================
def show_splash():
    splash = tk.Tk()
    splash.title("XFORGE")
    splash.attributes("-fullscreen", True)
    splash.configure(bg="#0a0f1a")
    
    # Center frame
    frame = tk.Frame(splash, bg="#0a0f1a")
    frame.place(relx=0.5, rely=0.5, anchor="center")
    
    # Main Title - Futuristic
    title = tk.Label(frame, text="XFORGE", font=("Helvetica", 72, "bold"), 
                     fg="#22c55e", bg="#0a0f1a")
    title.pack(pady=20)
    
    # Subtitle
    subtitle = tk.Label(frame, text="SELF-IMPROVEMENT MODULE", 
                        font=("Helvetica", 22, "normal"), 
                        fg="#64748b", bg="#0a0f1a")
    subtitle.pack(pady=5)
    
    # Tagline
    tagline = tk.Label(frame, text="Advanced • Secure • Intelligent", 
                       font=("Helvetica", 14, "italic"), 
                       fg="#94a3b8", bg="#0a0f1a")
    tagline.pack(pady=15)
    
    # Loading bar
    progress = ttk.Progressbar(frame, length=400, mode='indeterminate', 
                               style="TProgressbar")
    progress.pack(pady=30)
    progress.start(15)
    
    # Status text
    status = tk.Label(frame, text="Initializing Secure Environment...", 
                      font=("Helvetica", 13), fg="#64748b", bg="#0a0f1a")
    status.pack(pady=10)
    
    # Decorative lines
    line1 = tk.Label(frame, text="━" * 60, font=("Helvetica", 8), 
                     fg="#22c55e", bg="#0a0f1a")
    line1.pack()
    
    # Close splash after 2.5 seconds
    def close_splash():
        progress.stop()
        splash.destroy()
    
    splash.after(2500, close_splash)
    splash.mainloop()

# ==================== API KEY INPUT WINDOW ====================
def get_api_key():
    key_window = tk.Tk()
    key_window.title("XForge • Secure API Access")
    key_window.configure(bg="#0a0f1a")
    key_window.geometry("520x380")
    key_window.resizable(False, False)
    
    # Center on screen
    key_window.eval('tk::PlaceWindow . center')
    
    # Main container
    main_frame = tk.Frame(key_window, bg="#0a0f1a", padx=40, pady=40)
    main_frame.pack(expand=True, fill="both")
    
    # Header
    header = tk.Label(main_frame, text="🔐 API KEY REQUIRED", 
                      font=("Helvetica", 20, "bold"), fg="#22c55e", bg="#0a0f1a")
    header.pack(pady=(0, 20))
    
    # Description
    desc = tk.Label(main_frame, text="Enter your xAI Grok API key.\nIt will be used only for this session (never saved).", 
                    font=("Helvetica", 12), fg="#94a3b8", bg="#0a0f1a", justify="center")
    desc.pack(pady=(0, 25))
    
    # API Key Entry
    key_var = tk.StringVar()
    key_entry = tk.Entry(main_frame, textvariable=key_var, show="•", 
                         font=("Helvetica", 16), bg="#1e2937", fg="#e0e7ff",
                         insertbackground="#22c55e", relief="flat", bd=2)
    key_entry.pack(pady=10, ipady=12, fill="x")
    key_entry.focus_set()
    
    # Status label
    status_label = tk.Label(main_frame, text="", font=("Helvetica", 11), 
                            fg="#ef4444", bg="#0a0f1a")
    status_label.pack(pady=10)
    
    # Buttons
    button_frame = tk.Frame(main_frame, bg="#0a0f1a")
    button_frame.pack(pady=20)
    
    def validate_and_continue():
        key = key_var.get().strip()
        if not key or not key.startswith(("xai-", "sk-")):
            status_label.config(text="❌ Please enter a valid xAI API key", fg="#ef4444")
            return
        
        # Test the key quickly
        try:
            import openai
            client = openai.OpenAI(api_key=key, base_url="https://api.x.ai/v1")
            client.chat.completions.create(
                model="grok-4.3",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            os.environ["XAI_API_KEY"] = key
            status_label.config(text="✅ Key validated!", fg="#22c55e")
            key_window.after(800, key_window.destroy)
        except Exception as e:
            status_label.config(text=f"❌ Invalid key: {str(e)[:60]}", fg="#ef4444")
    
    def use_env_key():
        env_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        if env_key:
            os.environ["XAI_API_KEY"] = env_key
            key_window.destroy()
        else:
            status_label.config(text="❌ No environment key found. Please enter above.", fg="#ef4444")
    
    validate_btn = tk.Button(button_frame, text="✅ VALIDATE & CONTINUE", 
                             command=validate_and_continue, 
                             font=("Helvetica", 13, "bold"), bg="#22c55e", fg="white",
                             padx=30, pady=12, relief="flat")
    validate_btn.pack(side="left", padx=15)
    
    env_btn = tk.Button(button_frame, text="🔑 USE ENVIRONMENT KEY", 
                        command=use_env_key, 
                        font=("Helvetica", 12), bg="#334155", fg="#e0e7ff",
                        padx=20, pady=12, relief="flat")
    env_btn.pack(side="left", padx=15)
    
    key_window.mainloop()
    return os.getenv("XAI_API_KEY")

# ==================== DEPENDENCY INSTALLATION ====================
def install_dependencies():
    print("\n🔧 Installing dependencies...")
    packages = ["openai", "pandas", "pydantic", "gradio", "requests"]
    for pkg in packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"   ✓ {pkg}")
        except ImportError:
            print(f"   Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])
    
    subprocess.check_call([sys.executable, "-m", "pip", "install", "jinja2>=3.1.5", "--quiet", "--upgrade"])
    print("✅ All dependencies ready.\n")

# ==================== LAUNCH MAIN APP ====================
def launch_sim():
    print("🚀 Launching XForge Self-Improvement UI...")
    time.sleep(1)
    
    sim_path = Path(__file__).parent / "SIM.py"
    if not sim_path.exists():
        print("❌ SIM.py not found in the same folder!")
        sys.exit(1)
    
    # Launch in new process
    subprocess.Popen([sys.executable, str(sim_path)])
    print("✅ XForge Self-Improvement is now running at http://127.0.0.1:7860")
    print("   You can close this launcher window.")

# ==================== MAIN LAUNCHER FLOW ====================
if __name__ == "__main__":
    # 1. Show futuristic splash
    show_splash()
    
    # 2. Check for existing key
    existing_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not existing_key:
        print("🔐 No API key detected in environment. Opening secure input window...")
        key = get_api_key()
        if not key:
            print("❌ No API key provided. Exiting.")
            sys.exit(0)
    else:
        print(f"🔑 Using existing API key from environment.")
    
    # 3. Install dependencies
    install_dependencies()
    
    # 4. Launch the main app
    launch_sim()
    
    print("\n✨ XForge Launcher complete. Enjoy your self-improvement session!")
