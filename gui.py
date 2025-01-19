import tkinter as tk
from tkinter import filedialog, messagebox
from metadata_manager import MetadataManager

class MetadataGUI:
    """
    GUI for:
      - Selecting an MP3 file.
      - Displaying all metadata (including extra fields).
      - Editing basic fields through Entry widgets.
      - Selecting options (removing cover art, automatic corrections).
      - Saving changes to the file.
    """

    def __init__(self, root, config_file="config.json"):
        self.root = root
        self.root.title("Music Metadata Manager")
        self.config_file = config_file

        self.manager = None   # Instance of MetadataManager
        self.loaded_file = None

        # ------------------------------
        # 1) File loading section
        # ------------------------------
        frame_load = tk.Frame(self.root)
        frame_load.pack(fill="x", padx=5, pady=5)

        btn_select_file = tk.Button(frame_load, text="Select MP3", command=self.load_mp3)
        btn_select_file.pack(side=tk.LEFT, padx=5)

        self.lbl_file_path = tk.Label(frame_load, text="No file selected", anchor="w")
        self.lbl_file_path.pack(side=tk.LEFT, fill="x", expand=True)

        # ------------------------------
        # 2) Options section (checkboxes)
        # ------------------------------
        frame_options = tk.LabelFrame(self.root, text="Options")
        frame_options.pack(fill="x", padx=5, pady=5)

        self.var_remove_cover = tk.BooleanVar(value=False)
        chk_cover = tk.Checkbutton(frame_options, text="Remove Cover Art", variable=self.var_remove_cover)
        chk_cover.pack(anchor="w", padx=5, pady=2)

        self.var_apply_corrections = tk.BooleanVar(value=False)
        chk_corrections = tk.Checkbutton(frame_options, text="Apply Automatic Corrections", variable=self.var_apply_corrections)
        chk_corrections.pack(anchor="w", padx=5, pady=2)

        # ------------------------------
        # 3) Basic field editing section
        # ------------------------------
        frame_edit = tk.LabelFrame(self.root, text="Edit Basic Fields")
        frame_edit.pack(fill="x", padx=5, pady=5)

        # Title
        tk.Label(frame_edit, text="Title:").grid(row=0, column=0, sticky="w")
        self.entry_title = tk.Entry(frame_edit, width=50)
        self.entry_title.grid(row=0, column=1, padx=5, pady=2)

        # Artist
        tk.Label(frame_edit, text="Artist:").grid(row=1, column=0, sticky="w")
        self.entry_artist = tk.Entry(frame_edit, width=50)
        self.entry_artist.grid(row=1, column=1, padx=5, pady=2)

        # Album
        tk.Label(frame_edit, text="Album:").grid(row=2, column=0, sticky="w")
        self.entry_album = tk.Entry(frame_edit, width=50)
        self.entry_album.grid(row=2, column=1, padx=5, pady=2)

        # Genre
        tk.Label(frame_edit, text="Genre:").grid(row=3, column=0, sticky="w")
        self.entry_genre = tk.Entry(frame_edit, width=50)
        self.entry_genre.grid(row=3, column=1, padx=5, pady=2)

        # ------------------------------
        # 4) Metadata display section
        # ------------------------------
        frame_metadata = tk.Frame(self.root)
        frame_metadata.pack(fill="both", expand=True, padx=5, pady=5)

        self.txt_metadata = tk.Text(frame_metadata, wrap="none", height=15)
        self.txt_metadata.pack(side=tk.LEFT, fill="both", expand=True)

        scrollbar_y = tk.Scrollbar(frame_metadata, orient=tk.VERTICAL, command=self.txt_metadata.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill="y")
        self.txt_metadata["yscrollcommand"] = scrollbar_y.set

        # ------------------------------
        # 5) Action buttons section
        # ------------------------------
        frame_actions = tk.Frame(self.root)
        frame_actions.pack(fill="x", padx=5, pady=5)

        btn_refresh = tk.Button(frame_actions, text="Refresh Metadata View", command=self.show_all_metadata)
        btn_refresh.pack(side=tk.LEFT, padx=5)

        btn_save = tk.Button(frame_actions, text="Save Changes", command=self.save_changes)
        btn_save.pack(side=tk.LEFT, padx=5)

    # --------------------------------------------------------------------------
    # CALLBACKS
    # --------------------------------------------------------------------------
    def load_mp3(self):
        """Select an MP3 file and load it into the MetadataManager."""
        filepath = filedialog.askopenfilename(
            title="Select MP3 file",
            filetypes=[("MP3 Files", "*.mp3"), ("All Files", "*.*")]
        )
        if not filepath:
            return  # User canceled

        self.manager = MetadataManager(self.config_file)
        try:
            self.manager.load_file(filepath)
            self.loaded_file = filepath
            self.lbl_file_path.config(text=filepath)
            self.show_all_metadata()
            self.update_fields_from_manager()
        except Exception as e:
            messagebox.showerror("Error", f"Unable to load file: {e}")

    def show_all_metadata(self):
        """Display all metadata (EasyID3 and extra frames) in the Text widget."""
        if not self.manager or not self.loaded_file:
            self.txt_metadata.delete("1.0", tk.END)
            self.txt_metadata.insert(tk.END, "No file loaded.")
            return

        self.txt_metadata.delete("1.0", tk.END)

        # Display EasyID3 fields
        self.txt_metadata.insert(tk.END, "=== EasyID3 Metadata ===\n")
        if self.manager.audio_easy:
            for field_name, values in self.manager.audio_easy.items():
                self.txt_metadata.insert(tk.END, f"{field_name}: {values}\n")
        else:
            self.txt_metadata.insert(tk.END, "No EasyID3 metadata.\n")

        # Display extra ID3 frames
        self.txt_metadata.insert(tk.END, "\n=== Extra ID3 Frames ===\n")
        if self.manager.audio_id3:
            easy_keys_lower = [k.lower() for k in (self.manager.audio_easy.keys() if self.manager.audio_easy else [])]
            for frame_id in self.manager.audio_id3.keys():
                if frame_id.lower() not in easy_keys_lower:
                    frame_obj = self.manager.audio_id3[frame_id]
                    self.txt_metadata.insert(tk.END, f"{frame_id}: {frame_obj}\n")
        else:
            self.txt_metadata.insert(tk.END, "No extra ID3 frames.\n")

        # Display MP3 info
        if self.manager.audio_info:
            self.txt_metadata.insert(tk.END, "\n=== MP3 Info ===\n")
            self.txt_metadata.insert(tk.END, f"Bitrate: {self.manager.audio_info.bitrate} bps\n")
            self.txt_metadata.insert(tk.END, f"Sample Rate: {self.manager.audio_info.sample_rate} Hz\n")
            self.txt_metadata.insert(tk.END, f"Channels: {self.manager.audio_info.channels}\n")
            duration = round(self.manager.audio_info.length, 2)
            self.txt_metadata.insert(tk.END, f"Duration: ~{duration} s\n")

    def update_fields_from_manager(self):
        """Update Entry widgets (title, artist, album, genre) with current metadata."""
        if not self.manager:
            return
        self.entry_title.delete(0, tk.END)
        self.entry_title.insert(0, self.manager.get_field("title") or "")

        self.entry_artist.delete(0, tk.END)
        self.entry_artist.insert(0, self.manager.get_field("artist") or "")

        self.entry_album.delete(0, tk.END)
        self.entry_album.insert(0, self.manager.get_field("album") or "")

        self.entry_genre.delete(0, tk.END)
        self.entry_genre.insert(0, self.manager.get_field("genre") or "")

    def apply_fields_to_manager(self):
        """Write values from Entry widgets into the metadata before corrections or save."""
        if not self.manager:
            return
        self.manager.set_field("title", self.entry_title.get())
        self.manager.set_field("artist", self.entry_artist.get())
        self.manager.set_field("album", self.entry_album.get())
        self.manager.set_field("genre", self.entry_genre.get())

    def save_changes(self):
        """
        1) Update metadata with user input.
        2) Apply automatic corrections if selected.
        3) Remove cover art if selected.
        4) Save changes to file.
        5) Refresh the metadata view.
        """
        if not self.manager or not self.loaded_file:
            messagebox.showwarning("Warning", "No file loaded.")
            return

        self.apply_fields_to_manager()

        if self.var_apply_corrections.get():
            try:
                self.manager.check_and_correct_all()
            except Exception as e:
                messagebox.showerror("Error", f"Error during automatic corrections: {e}")
                return

        if self.var_remove_cover.get():
            try:
                self.manager.remove_album_art()
            except Exception as e:
                messagebox.showerror("Error", f"Unable to remove cover art: {e}")
                return

        try:
            self.manager.save_file()
            messagebox.showinfo("Success", "Changes saved successfully.")
            self.show_all_metadata()
            self.update_fields_from_manager()
        except Exception as e:
            messagebox.showerror("Error", f"Unable to save file: {e}")


def main():
    import os
    path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(path, 'config.json')

    root = tk.Tk()
    app = MetadataGUI(root, config_path)
    root.mainloop()

if __name__ == "__main__":
    main()
