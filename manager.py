import os
import json
import time
import logging
from pathlib import Path
from shutil import move
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import streamlit as st

# Configuration setup
CONFIG_FILE = Path.home() / ".file_organizer_config.json"
log_buffer = deque(maxlen=50)

def load_config():
    if not CONFIG_FILE.exists():
        return {"source_dir": "", "extensions": {}}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

class OrganizerHandler(FileSystemEventHandler):
    def __init__(self):
        self.config = load_config()
        
    def on_modified(self, event):
        if not event.is_directory:
            return
            
        with os.scandir(self.config["source_dir"]) as entries:
            for entry in entries:
                if entry.is_file():
                    self.process_file(entry)

    def process_file(self, entry):
        name = entry.name
        ext = Path(name).suffix.lower()
        
        if ext in self.config["extensions"]:
            dest = Path(self.config["extensions"][ext])
            self.move_file(entry, dest, name)

    def move_file(self, entry, dest_dir, name):
        try:
            dest_dir.mkdir(exist_ok=True, parents=True)
            dest_path = dest_dir / name
            
            if dest_path.exists():
                name = self.make_unique(dest_dir, name)
                dest_path = dest_dir / name
                
            move(entry.path, str(dest_path))
            log_buffer.append(f"Moved: {name} → {dest_dir}")
        except Exception as e:
            log_buffer.append(f"Error moving {name}: {str(e)}")

    def make_unique(self, dest_dir, filename):
        base = Path(filename).stem
        ext = Path(filename).suffix
        counter = 1
        while True:
            new_name = f"{base}({counter}){ext}"
            new_path = dest_dir / new_name
            if not new_path.exists():
                return new_name
            counter += 1

def main():
    st.title("📁 Dynamic File Organizer")
    config = load_config()

    # Configuration Section
    with st.expander("⚙️ Configuration", expanded=True):
        source_dir = st.text_input("Source Directory", config.get("source_dir", ""))
        if st.button("Save Source Directory"):
            config["source_dir"] = source_dir
            save_config(config)
            st.success("Source directory saved!")
            st.rerun()

    # Extension Management
    with st.expander("📄 File Type Rules", expanded=True):
        st.write("Current file type rules:")
        
        for ext, dest in config["extensions"].items():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.code(ext)
            with col2:
                st.text(dest)
            with col3:
                if st.button(f"Remove {ext}"):
                    del config["extensions"][ext]
                    save_config(config)
                    st.rerun()

        new_ext = st.text_input("New File Extension (e.g., .mp3)")
        new_dest = st.text_input("Destination Folder for this Extension")
        if st.button("Add New Rule"):
            if new_ext and new_dest:
                config["extensions"][new_ext.lower()] = new_dest
                save_config(config)
                st.rerun()
            else:
                st.error("Both fields are required!")

    # Organizer Control
    with st.expander("🎛️ Organizer Controls", expanded=True):
        if "observer" not in st.session_state:
            st.session_state.observer = None

        if st.session_state.observer and st.session_state.observer.is_alive():
            st.success("✅ Organizer is running")
            if st.button("Stop Organizer"):
                st.session_state.observer.stop()
                st.session_state.observer = None
                st.rerun()
        else:
            if st.button("Start Organizer"):
                if not config["source_dir"]:
                    st.error("Please set a source directory first!")
                    return
                
                handler = OrganizerHandler()
                observer = Observer()
                observer.schedule(handler, config["source_dir"], recursive=True)
                observer.start()
                st.session_state.observer = observer
                st.rerun()

    # Live Logs
    with st.expander("📜 Activity Logs", expanded=True):
        if st.button("Clear Logs"):
            log_buffer.clear()
        st.text_area("Recent Activity", "\n".join(log_buffer), height=200)

if __name__ == "__main__":
    main()