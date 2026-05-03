# ============================================================
# splash_screen.py  —  xForgeTrader V11 Graphical Splash
# Shows a clean loading screen while the app initializes
# ============================================================

import tkinter as tk
from tkinter import ttk
import sys

def show_splash():
    root = tk.Tk()
    root.title("xForgeTrader V11")
    root.geometry("420x240")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    
    # Center on screen
    root.eval('tk::PlaceWindow . center')
    
    # Title
    title = tk.Label(root, text="xForgeTrader V11", 
                     font=("Helvetica", 26, "bold"), fg="#1a73e8")
    title.pack(pady=(30, 5))
    
    # Subtitle
    subtitle = tk.Label(root, text="Profit Recommendation Engine", 
                        font=("Helvetica", 14), fg="#555555")
    subtitle.pack()
    
    # Status line
    status = tk.Label(root, text="Initializing modules & data layer...", 
                      font=("Helvetica", 11), fg="#666666")
    status.pack(pady=15)
    
    # Progress bar
    progress = ttk.Progressbar(root, orient="horizontal", length=320, 
                               mode="indeterminate")
    progress.pack(pady=10)
    progress.start(12)
    
    # Footer
    footer = tk.Label(root, text="Grok-Powered • Self-Improving • Demo Ready", 
                      font=("Helvetica", 9), fg="#888888")
    footer.pack(pady=10)
    
    # Auto-close after 7 seconds (or user can close manually)
    root.after(7000, root.destroy)
    
    root.mainloop()

if __name__ == "__main__":
    show_splash()
