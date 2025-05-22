import io
import os
import random
import subprocess
import threading

import customtkinter as ctk
import pygame
from PIL import Image
from customtkinter import CTkImage
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3

SUPPORTED_FORMATS = ['.mp3', '.wav', '.ogg']

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Style USB Player")
        self.root.geometry("460x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        pygame.mixer.init()
        self.music_files = []
        self.current_index = 0
        self.paused = False
        self.shuffle = False
        self.folders = {}

        # Top frame to hold everything horizontally centered
        self.top_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.top_frame.pack(pady=(15, 5), padx=10, fill="x")

        # Left controls frame: Shuffle and Search USB stacked vertically
        self.left_controls = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.left_controls.grid(row=0, column=0, sticky="n")

        self.shuffle_button = ctk.CTkButton(self.left_controls, text="🔀 Shuffle: Off", command=self.toggle_shuffle,
                                            width=140, height=35, corner_radius=18, fg_color="#121212", text_color="white",
                                            hover_color="#1DB954")
        self.shuffle_button.pack(pady=(0, 10))

        self.scan_button = ctk.CTkButton(self.left_controls, text="🔄 USB durchsuchen", command=self.scan_usb,
                                        width=140, height=35, corner_radius=18, fg_color="#121212", text_color="white",
                                        hover_color="#1DB954")
        self.scan_button.pack()

        # Then add this button somewhere in your UI, e.g. in left_controls:
        self.bt_button = ctk.CTkButton(self.left_controls, text="🔵 Bluetooth Setup", command=self.open_bluetoothctl,
                                    width=140, height=35, corner_radius=18, fg_color="#121212", text_color="white",
                                    hover_color="#1DB954")
        self.bt_button.pack(pady=(10, 0))

        # Album cover in center
        self.album_art_label = ctk.CTkLabel(self.top_frame, text="", width=180, height=180)
        self.album_art_label.grid(row=0, column=1, padx=15)

        # Right controls frame: Volume label + vertical slider stacked
        self.right_controls = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.right_controls.grid(row=0, column=2, sticky="n")

        self.volume_label = ctk.CTkLabel(self.right_controls, text="Lautstärke", text_color="white", font=("Arial", 12))
        self.volume_label.pack(pady=(0, 10))

        # Vertical volume slider with inverted direction
        self.volume_slider = ctk.CTkSlider(self.right_controls, from_=0, to=100, command=self.set_volume,
                                        progress_color="#1DB954", orientation="vertical", height=150, width=20)
        self.volume_slider.set(70)
        self.volume_slider.pack()

        # Title & Artist below top frame
        self.track_title = ctk.CTkLabel(root, text="", font=("Arial", 16, "bold"), text_color="white")
        self.track_title.pack(pady=(10, 0))
        self.track_artist = ctk.CTkLabel(root, text="", font=("Arial", 12), text_color="#B3B3B3")
        self.track_artist.pack(pady=(0, 10))

        # Playback controls frame (Play, Pause, Next) horizontally centered
        self.controls_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.controls_frame.pack(pady=5)

        btn_width, btn_height = 50, 50
        font_size = 20

        self.play_button = ctk.CTkButton(self.controls_frame, text="▶", command=self.play_music,
                                        width=btn_width, height=btn_height, corner_radius=btn_height // 2,
                                        font=("Arial", font_size), fg_color="#1DB954")
        self.play_button.grid(row=0, column=1, padx=5)

        self.pause_button = ctk.CTkButton(self.controls_frame, text="⏸", command=self.pause_music,
                                        width=btn_width, height=btn_height, corner_radius=btn_height // 2,
                                        font=("Arial", font_size), fg_color="#1DB954")
        self.pause_button.grid(row=0, column=2, padx=5)

        self.next_button = ctk.CTkButton(self.controls_frame, text="⏭", command=self.play_next,
                                        width=btn_width, height=btn_height, corner_radius=btn_height // 2,
                                        font=("Arial", font_size), fg_color="#1DB954")
        self.next_button.grid(row=0, column=3, padx=5)

        # Scrollable frame for folders & playlist
        self.content_frame = ctk.CTkScrollableFrame(root, width=420, height=260, corner_radius=15)
        self.content_frame.pack(pady=(10, 10))

        self.folder_buttons = []
        self.track_buttons = []

        self.status_label = ctk.CTkLabel(root, text="Status: Bereit", text_color="#1DB954", font=("Arial", 12))
        self.status_label.pack(pady=5)

        pygame.mixer.music.set_volume(0.7)
        self.check_music_end()

        # Show folders if any
        self.show_folders()

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        status = "On" if self.shuffle else "Off"
        self.shuffle_button.configure(text=f"🔀 Shuffle: {status}")

    def open_bluetoothctl(self):
        threading.Thread(target=self.show_bluetooth_devices_popup, daemon=True).start()

    def show_bluetooth_devices_popup(self):
        try:
            # Start scanning
            subprocess.run(['bluetoothctl', 'scan', 'on'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['sleep', '5'])
            subprocess.run(['bluetoothctl', 'scan', 'off'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Get list of devices
            devices_out = subprocess.check_output(['bluetoothctl', 'devices'], text=True)
            devices = []

            for line in devices_out.splitlines():
                parts = line.split(' ', 2)
                if len(parts) == 3:
                    mac, name = parts[1], parts[2]
                    devices.append((name, mac))

            self.root.after(0, lambda: self.show_devices_window(devices))

        except Exception as e:
            self.root.after(0, lambda: self.status_label.configure(text=f"Bluetooth Fehler: {e}"))

    def show_devices_window(self, devices):
        popup = ctk.CTkToplevel(self.root)
        popup.title("Bluetooth Geräte")
        popup.geometry("350x450")

        title = ctk.CTkLabel(popup, text="Gefundene Bluetooth Geräte", font=("Arial", 15, "bold"))
        title.pack(pady=10)

        frame = ctk.CTkScrollableFrame(popup, width=320, height=350)
        frame.pack(pady=5, padx=10)

        if devices:
            for name, mac in devices:
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", pady=2)

                name_label = ctk.CTkLabel(row, text=name, width=150, anchor="w")
                name_label.pack(side="left", padx=(0, 10))

                mac_label = ctk.CTkLabel(row, text=mac, width=110, anchor="w", text_color="#AAAAAA")
                mac_label.pack(side="left")

                connect_btn = ctk.CTkButton(row, text="Verbinden", width=80, height=28, font=("Arial", 11),
                                            command=lambda m=mac: self.connect_to_bluetooth_device(m))
                connect_btn.pack(side="right")
        else:
            ctk.CTkLabel(frame, text="Keine Geräte gefunden.", font=("Arial", 12)).pack(pady=20)

    def connect_to_bluetooth_device(self, mac_address):
        def connect():
            try:
                result = subprocess.check_output(['bluetoothctl', 'connect', mac_address], text=True,
                                                stderr=subprocess.STDOUT)
                if "Connection successful" in result:
                    self.root.after(0, lambda: self.status_label.configure(text=f"Verbunden mit {mac_address}"))
                else:
                    self.root.after(0, lambda: self.status_label.configure(
                        text=f"Verbindung fehlgeschlagen: {mac_address}"))
            except subprocess.CalledProcessError as e:
                    error_msg = e.output.strip() if hasattr(e, 'output') else str(e)
                    self.root.after(0, lambda msg=error_msg: self.status_label.configure(text=f"Fehler: {msg}"))


        threading.Thread(target=connect, daemon=True).start()

    def find_usb_drives(self):
        # Use lsblk to find removable USB drives on Linux
        removable = []
        try:
            output = subprocess.check_output(['lsblk', '-o', 'NAME,RM,MOUNTPOINT'], text=True)
            for line in output.splitlines()[1:]:  # skip header
                parts = line.split()
                if len(parts) >= 3:
                    name, rm, mountpoint = parts[0], parts[1], parts[2]
                    if rm == '1' and mountpoint != '':
                        removable.append(mountpoint)
        except Exception as e:
            print(f"Fehler beim Finden von USB-Laufwerken: {e}")
        return removable

    def find_music_files(self, drive):
        folder_dict = {}
        for root, dirs, files in os.walk(drive):
            track_list = []
            for file in files:
                if any(file.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
                    track_list.append(os.path.join(root, file))
            if track_list:
                folder_dict[root] = track_list
        return folder_dict

    def scan_usb(self):
        self.status_label.configure(text="USB wird durchsucht...")
        usb_drives = self.find_usb_drives()
        if not usb_drives:
            self.status_label.configure(text="Kein USB-Laufwerk gefunden.")
            return

        for drive in usb_drives:
            folder_tracks = self.find_music_files(drive)
            if folder_tracks:
                self.folders = folder_tracks
                self.show_folders()
                self.status_label.configure(text=f"{sum(len(v) for v in folder_tracks.values())} Titel gefunden.")
                return

        self.status_label.configure(text="Keine Musik auf USB gefunden.")

    def show_folders(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.folder_buttons = []
        for folder in self.folders:
            folder_name = os.path.basename(folder.rstrip("/\\"))
            btn = ctk.CTkButton(self.content_frame, text=folder_name, width=400, height=38,
                                corner_radius=10, fg_color="#121212", text_color="white",
                                hover_color="#1DB954", anchor="w",
                                command=lambda f=folder: self.show_playlist(f))
            btn.pack(pady=2)
            self.folder_buttons.append(btn)

    def show_playlist(self, folder):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.back_button = ctk.CTkButton(self.content_frame, text="...", width=40, height=30,
                                        corner_radius=10, fg_color="#121212", text_color="white",
                                        hover_color="#1DB954", command=self.show_folders)
        self.back_button.pack(pady=(5, 10), anchor="w")

        self.music_files = self.folders[folder]
        self.current_index = 0

        folder_name = os.path.basename(folder.rstrip("/\\"))
        header = ctk.CTkLabel(self.content_frame, text=folder_name, font=("Arial", 14, "bold"), text_color="#1DB954")
        header.pack(pady=(0, 8))

        self.track_buttons = []
        for i, track in enumerate(self.music_files):
            title = os.path.basename(track)
            btn = ctk.CTkButton(self.content_frame, text=title, width=400, height=36, corner_radius=10,
                                fg_color="#121212", text_color="white", hover_color="#1DB954",
                                anchor="w", command=lambda idx=i: self.play_track(idx))
            btn.pack(pady=1)
            self.track_buttons.append(btn)

    def play_track(self, index):
        self.current_index = index
        self.play_music()

    def display_album_art(self, filepath):
        try:
            audio = MP3(filepath, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    artwork = tag.data
                    image = Image.open(io.BytesIO(artwork)).resize((180, 180))
                    photo = CTkImage(light_image=image, size=(180, 180))
                    self.album_art_label.configure(image=photo, text="")
                    self.album_art_label.image = photo
                    return
            self.album_art_label.configure(image=NONE, text="")
        except Exception:
            self.album_art_label.configure(image=NONE, text="")

    def check_music_end(self):
        if not pygame.mixer.music.get_busy() and not self.paused:
            self.play_next()
        self.root.after(1000, self.check_music_end)

    def play_music(self):
        if not self.music_files:
            self.status_label.configure(text="Keine Musik geladen.")
            return
        try:
            if self.shuffle:
                self.current_index = random.randint(0, len(self.music_files) - 1)
            file = self.music_files[self.current_index]
            pygame.mixer.music.load(file)
            pygame.mixer.music.play()
            self.paused = False
            audio = MP3(file, ID3=ID3)
            title = str(audio.tags.get('TIT2', os.path.basename(file)))
            artist = str(audio.tags.get('TPE1', 'Unbekannter Künstler'))
            self.track_title.configure(text=str(title))
            self.track_artist.configure(text=str(artist))
            self.status_label.configure(text=f"Spielt: {os.path.basename(file)}")
            self.display_album_art(file)
        except Exception as e:
            self.status_label.configure(text=f"Fehler: {str(e)}")

    def pause_music(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.status_label.configure(text="Fortgesetzt")
            self.paused = False
        else:
            pygame.mixer.music.pause()
            self.status_label.configure(text="Pausiert")
            self.paused = True

    def play_next(self):
        if not self.music_files:
            return
        self.current_index = (self.current_index + 1) % len(self.music_files)
        self.play_music()

    def set_volume(self, val):
        pygame.mixer.music.set_volume(float(val) / 100)

if __name__ == "__main__":
    root = ctk.CTk()
    app = MusicPlayer(root)
    root.mainloop()