import tkinter as tk
from tkinter import PhotoImage, BOTTOM
import subprocess
try:
    import vlc
except:
    p = subprocess.Popen([r"bin/vlc-3.0.1-win32.exe"])
    (output, err) = p.communicate()
    p_status = p.wait()
    import vlc
    
import threading
import time
from utils.utils import seconds_in_time_for_humans
import platform

# tipo y numero de fuente
LARGE_FONT = ("Verdana", 16)


class AudioPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.controller = controller
        self.parent._root().protocol("WM_DELETE_WINDOW", self.on_closing)
        # nombre del archivo cargado
        label_name_file = tk.Label(self, text=controller.data["name_file"], font=LARGE_FONT)
        label_name_file.pack(pady=10, padx=10)

        # del path obtenemos el nombre para realizar la consulta en la db
        self.name_for_get_file = self.controller.data["name_file"]
        # obtener el audio desde la db
        self.audio_file_from_db = self.controller.data["manage_db"].get_file(self.name_for_get_file)

        # obtener la longitud del audio desde la db
        self.len_current_audio_book = float(self.audio_file_from_db[2])

        # slide de reproducción de audio
        print(self.len_current_audio_book)
        self.timeslider = tk.Scale(self, from_=0, to=self.len_current_audio_book, resolution=1, orient=tk.HORIZONTAL,
                                   showvalue='no', activebackground="black", bg="#ffff00")
        self.timeslider.pack()
        self.timeslider.set(0)

        # label para mostar el tiempo de la reproducción
        self.time_elapsed = tk.Label(text=seconds_in_time_for_humans(0))
        self.time_elapsed.pack()

        # imagenes de iconos
        if platform.system() == "Windows":
            self.icon_play = PhotoImage(file="img/ic_play_arrow_black_24dp_1x.png")
            self.icon_pause = PhotoImage(file="img/ic_pause_black_24dp_1x.png")
            self.icon_stop = PhotoImage(file="img/ic_stop_black_24dp_1x.png")
            self.icon_return = PhotoImage(file="img/ic_home_black_24dp_1x.png")
        else:
            self.icon_play = PhotoImage(file="../img/ic_play_arrow_black_24dp_1x.png")
            self.icon_pause = PhotoImage(file="../img/ic_pause_black_24dp_1x.png")
            self.icon_stop = PhotoImage(file="../img/ic_stop_black_24dp_1x.png")
            self.icon_return = PhotoImage(file="../img/ic_home_black_24dp_1x.png")

        # boton de reproducir
        self.button_play = tk.Button(self, text="Reproducir",
                                     command=lambda: self.play_audio(), image=self.icon_play)
        self.button_play.pack()

        # boton de detener
        self.button_stop = tk.Button(self, text="DETENER",
                                     command=lambda: self.stop_audio(), image=self.icon_stop)

        button_return = tk.Button(self, text="ATRÁS",
                                  command=lambda: self.go_home(),
                                  image=self.icon_return)
        button_return.pack(side=BOTTOM)

        ############## PLAYER ##############
        self.Instance = vlc.Instance()
        self.player = self.Instance.media_player_new()
        # cargar el archivo de audio
        self.media = self.Instance.media_new(self.audio_file_from_db[1])

        # semaforos
        self.going_home = False
        self.update_time_elapsed()
        self.last_time = 0


    def play_audio(self):
        """
            Se encarga de iniciar los threads para reproducción de audio

        :return: None
        """

        # cambia el icono de reproducción
        self.change_image_button_play(True)

        # mostrar boton stop
        self.button_stop.pack()

        # obtiene desde donde se va iniciar el audio según la posición del slider en milisegundos
        print(self.timeslider.get())

        if self.player.get_state() == 0:
            self.different_time = float(self.audio_file_from_db[3]) * 1000
        else:
            self.different_time = self.timeslider.get() * 1000

        # crear e inicia threads para reproducir audio
        self.thread = threading.Thread(target=lambda: self.play_worker(self.different_time))
        self.thread.daemon = True
        self.thread.start()

        # verifica la vida de los threads
        self.play_check()

    def play_worker(self, other_time):
        """
            Se encarga de reproducir el audio.

        :param other_time: el tiempo inicial de reproducción de audio
        :return: None
        """

        # si esta en pause se encarga de mantener la misma posición de reproducción al volver a ejecutarse
        # en caso contrario obtiene cualquier otra posición y ejecuta el audio
        if (self.player.get_state() == 3):
            self.player.pause()
        else:
            self.player.set_media(self.media)
            self.player.play()
            self.player.set_time(int(other_time))
        time.sleep(1)
        while self.player.is_playing():
            print(self.player.get_time())
            self.last_time = self.player.get_time() / 1000

    def play_check(self):
        """
            Se encarga de verificar cuando el thread muera

        :return: None
        """
        if self.going_home:
            self.stop_audio()
        # si el thread esta vivo mantiene actualizado el slider de reproducción
        # en caso contrario hace el cambio de iconos en botones
        if self.thread.is_alive():
            self.update_time_slider()
            self.after(1, self.play_check)
        else:
            self.change_image_button_play(False)
            self.button_stop.pack_forget()
            print("saliedo")
            if self.player.get_state() == 6:
                self.stop_audio()
            self.controller.data["manage_db"].set_last_time(self.controller.data["name_file"], self.last_time)

    def change_image_button_play(self, start):
        """
            Cambia la imagen del icono
            True el audio se esta ejecutando entonces muestra el icono de pausa
            False el audio esta pausado muestra el icono de play
        :param start: True o False
        :return: None
        """
        if start:
            self.button_play.config(image=self.icon_pause, command=lambda: self.pause_audio())
        else:
            self.button_play.config(image=self.icon_play, command=lambda: self.play_audio())

    def pause_audio(self):
        """
            Se encarga de pausar el audio.
        :return: None
        """
        self.player.pause()

    def stop_audio(self):
        """
            se encarga de detener el audio
        :return: None
        """
        self.player.stop()
        self.timeslider.set(0)

    def update_time_elapsed(self):
        """
            mantiene el label de tiempo y el slider de reproducción sincronizados

        :return: None
        """
        self.time_elapsed.config(text=seconds_in_time_for_humans(self.timeslider.get()))
        self.after(1, self.update_time_elapsed)

    def update_time_slider(self):
        """
            Obtiene la posición del repdocutor, la convierte a segundos y fija al slider de reproduccion
            en esa posición

        :return: None
        """
        self.timeslider.set(self.player.get_time()/1000)

    def go_home(self):
        self.going_home = True

        if self.player.get_state() == 3 or self.player.get_state() == 4:
            self.controller.data["manage_db"].set_last_time(self.controller.data["name_file"], self.last_time)

        self.time_elapsed.pack_forget()
        self.controller.data["path_file"] = ""
        self.controller.data["name_file"] = ""
        if platform.system() == "Windows":
            height = 380
        else:
            height = 380
        self.controller.show_frame(self.controller.data["menu_frame"], 450, height)

    def on_closing(self):
        try:
            if self.player.get_state() == 3 or self.player.get_state() == 4:
                self.controller.data["manage_db"].set_last_time(self.controller.data["name_file"], self.last_time)
                self.stop_audio()
        except:
            pass
        self.parent._root().destroy()

