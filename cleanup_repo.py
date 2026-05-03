#!/usr/bin/env python3
"""
Repo Cleanup Script for https://github.com/JeffStone69/GRO
Deletes all junk, old versions, backups, and generated files.
Run this from the repo root (where FORGE/ is located).
"""

import os
import shutil

def cleanup_repo():
    root = os.getcwd()
    print(f"🧹 Starting cleanup from: {root}\n")

    # 1. Root .DS_Store
    root_ds = os.path.join(root, ".DS_Store")
    if os.path.exists(root_ds):
        os.remove(root_ds)
        print("✅ Removed: .DS_Store (root)")
    else:
        print("ℹ️  .DS_Store (root) not found — skipping")

    # 2. FORGE folder path
    forge_dir = os.path.join(root, "FORGE")
    if not os.path.exists(forge_dir):
        print("❌ FORGE/ folder not found! Aborting.")
        return

    # 3. FORGE/.DS_Store
    forge_ds = os.path.join(forge_dir, ".DS_Store")
    if os.path.exists(forge_ds):
        os.remove(forge_ds)
        print("✅ Removed: FORGE/.DS_Store")
    else:
        print("ℹ️  FORGE/.DS_Store not found — skipping")

    # 4. Folders to delete entirely
    folders_to_delete = [".gradio", "backups", "versions"]
    for folder in folders_to_delete:
        path = os.path.join(forge_dir, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"✅ Removed folder: {folder}/ (and all contents)")
        else:
            print(f"ℹ️  Folder {folder}/ not found — skipping")

    # 5. Files to delete
    files_to_delete = ["xforge_trader.old.py", "xforge_self_improve.db"]
    for file in files_to_delete:
        path = os.path.join(forge_dir, file)
        if os.path.exists(path):
            os.remove(path)
            print(f"✅ Removed file: {file}")
        else:
            print(f"ℹ️  File {file} not found — skipping")

    print("\n🎉 Cleanup complete!")
    print("Next steps:")
    print("  git add -u")
    print("  git commit -m \"Cleanup: removed junk, old versions, backups, and generated files\"")
    print("  git push")

if __name__ == "__main__":
    cleanup_repo()
