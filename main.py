from kivy.lang import Builder
from kivy.config import Config
from kivy.storage.dictstore import DictStore
from kivy.properties import StringProperty, ObjectProperty
from kivy.core.window import Window
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.list import TwoLineIconListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
from kivymd.toast import toast

from pychromecast.controllers.media import MEDIA_PLAYER_STATE_PAUSED

from ytmpd import build_mpd, CODECS, format_mime

import pychromecast
import zeroconf
import slider2
from ytdlhack import FixedYoutubeDL
import youtube_dl
from strserver import serve_async
import socket


CORS_PROXY = "http://192.168.178.20:8000/"
PORT = 47080

KV = r'''   

#:import time time
 
<CastItem>:
    on_release: app.select_cast(self.device)
    text: self.device[3]
    secondary_text: self.device[2]
    IconLeftWidget:
        icon: root.icon


BoxLayout:
    orientation: "vertical"
    
    MDToolbar:
        title: "Cast Remote"
        id: toolbar
        right_action_items: [["cast", lambda x: app.show_select_dialog()], ["brightness-6", lambda x: app.switch_theme_style()]]
    
    BoxLayout:
        height: self.minimum_height
        size_hint: 1, None
        padding: dp(10), dp(10), dp(10), 0 # ltrb
        spacing: dp(10)
        
        MDDropDownItem:
            id: resolution_dropdown
            text: "2160p"
            pos_hint: {'center_y': 0.5}
            on_release: app.resolution_menu.open()
                
        MDTextField:
            id: url_text_field
            hint_text: "Cast URL"
        
        MDIconButton:
            icon: "delete"
            on_release: url_text_field.text = ""
            
        MDIconButton:
            icon: "send"
            on_release: app.cast_url(url_text_field.text)

    
    BoxLayout:
        height: self.minimum_height
        size_hint: 1, None
        height: sp(32)
        padding: dp(10), 0 # hv
        
        MDSlider2:
            id: seek_slider
            min: 0
            max: 100
            value: 0
            on_active: if not self.active: app.seek(self.value)
            hint_text: app.format_time(self.value)
    
    BoxLayout:
        height: self.minimum_height
        size_hint: 1, None
        padding: "10dp", 0
        
        MDIconButton:
            icon: "play"
            id: play_button
            pos_hint: {'center_y': 0.5}
            user_font_size: "32sp"
            on_press: app.play_pause()
        MDLabel:
            id: time_label
            size_hint: 1, None
            height: self.texture_size[1]
            pos_hint: {'center_y': 0.5}
        MDIconButton:
            id: stop_button
            icon: "stop"
            pos_hint: {'center_y': 0.5, 'center_x': 1}
            user_font_size: "32sp"
            on_press: app.stop_button()
            
    GridLayout:
        height: self.minimum_height
        size_hint: 1, None
        padding:  dp(10), 0
        cols: 2
        row_default_height: mute_button.height
        
        MDIconButton:
            icon: "volume_high"
            id: mute_button
            #pos_hint: {'center_y': 0.5}
            user_font_size: sp(32)
            on_press: app.mute()

        MDSlider2:
            id: volume_slider
            min: 0
            max: 100
            value: 100
            pos_hint: {'center_y': 0.5}
            on_active: if not self.active: app.set_volume(self.value)
            hint_text: "{:.0f}%".format(self.value)  # fstring does not trigger updates
        
        AnchorLayout:
            anchor_x: "left"
            anchor_y: "center"
            width: mute_button.width + sp(10)
            size_hint_x: None
            
            MDDropDownItem:
                id: rate_dropdown
                text: "1.25x"
                height: volume_slider.height
                pos_hint: {'center_y': 0.5}
                on_release: app.rate_menu.open()
                
        MDSlider2:
            id: rate_slider
            min: 0.5 # https://developers.google.com/android/reference/com/google/android/gms/cast/MediaLoadOptions#PLAYBACK_RATE_MIN
            max: 2
            value: 1
            pos_hint: {'center_y': 0.5}
            on_active: if not self.active: app.set_rate(self.value)
            hint_text: "{:.2f}%".format(self.value)
         
    ScrollView:
        GridLayout:
            cols: 1
            adaptive_size: True
            size_hint: 1, None
            padding: "10dp"
            spacing: "10dp"
            height: self.minimum_height
            
            MDLabel:
                id: status_label
                height: self.texture_size[1]
                size_hint_y: None
'''


class CastItem(TwoLineIconListItem):
    icon = StringProperty()
    device = ObjectProperty()


class Settings:
    key = "settings"
    theme = "Dark"
    last_cast = None
    last_uuid = None
    last_url = None
    last_resolution = None
    
    
def update_dialog_items(dialog, items):
    dialog.ids.box_items.clear_widgets()

    # copied from create_dialog_items
    height = 0
    for item in items:
        height += item.height  # calculate height contents
        dialog.edit_padding_for_item(item)
        dialog.ids.box_items.add_widget(item)

    if height > Window.height:
        dialog.set_normal_height()
        dialog.ids.scroll.height = dialog.get_normal_height()
    else:
        dialog.ids.scroll.height = height


class CastRemoteApp(MDApp):
    cast_dialog = None
    cast_dialog_items = None
    browser = None
    cast = None
    cast_status = None
    media_status = None
    first_connect = False
    is_playing = False
    seeking = False
    max_resolution = 2160

    @staticmethod
    def format_time(seconds):
        s = int(seconds)
        return f"{s // 3600}:{s // 60 % 60:02}:{s % 60:02}" if s >= 3600 else f"{s // 60}:{s % 60:02}"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)        
        self.settings = store.get(Settings.key)["settings"]

        self.screen = Builder.load_string(KV)
        self.theme_cls.theme_style = self.settings.theme
        self.update_state()

        self.cast_listener = pychromecast.CastListener(self.update_chromecast_discovery, self.update_chromecast_discovery, self.update_chromecast_discovery)
        self.zconf = zeroconf.Zeroconf()
        self.browser = pychromecast.start_discovery(self.cast_listener, self.zconf)

        Clock.schedule_interval(self.tick, 0.2)

        label = self.screen.ids.volume_slider.ids.hint_label
        # label.text_size = None, None
        print(label.text_size)
        # hack_slider(self.screen.ids.volume_slider, lambda x: f"{round(x)}%")
        # hack_slider(self.screen.ids.seek_slider, lambda x: format_time(x))

        self.rate_menu = MDDropdownMenu(
            caller=self.screen.ids.rate_dropdown,
            items=[{"text": f"{x}x", "bot_pad": "12dp"}
                   for x in (0.5, 0.75, 1, 1.25, 1.5, 1.75, 2)],
            width_mult=2)
        self.rate_menu.bind(on_release=self.on_rate_menu)

        self.resolution_menu = MDDropdownMenu(
            caller=self.screen.ids.resolution_dropdown,
            items=[{"text": f"{x}p", "bot_pad": "12dp"}
                   for x in (2160, 1440, 1080, 720, 480, 360, 240, 144)],
            width_mult=2)
        self.resolution_menu.bind(on_release=self.on_resolution_menu)

        self.screen.ids.url_text_field.text = self.settings.last_url or ""
        self.max_resolution = self.settings.last_resolution or 2160
        self.screen.ids.resolution_dropdown.text = f"{self.max_resolution}p"
        
        self.serve_files = {}
        self.serv_thread = serve_async(self.serve_files, PORT)

    def on_rate_menu(self, menu, item):
        self.set_rate(float(item.text[:-1]))
        menu.dismiss()
        
    def on_resolution_menu(self, menu, item):
        self.settings.last_resolution = self.max_resolution = int(item.text[:-1])
        self.save()
        self.screen.ids.resolution_dropdown.text = item.text
        menu.dismiss()

    def update_chromecast_discovery(self, *args):
        self.cast_dialog_items = [
            CastItem(device=device, icon="monitor")
            for device in self.cast_listener.devices
        ]
        self.cast_dialog_items.sort(key=lambda i: i.text)
        if not self.cast and self.settings.last_uuid and not self.first_connect:
            devices = [dev for dev in self.cast_listener.devices if dev[1] == self.settings.last_uuid]
            if devices:
                self.select_cast(devices[0])
        if self.cast_dialog:
            update_dialog_items(self.cast_dialog, self.cast_dialog_items)
    
    def tick(self, dt):
        self.update_state()

    def build(self):
        return self.screen

    def on_stop(self):
        self.save()

    def on_pause(self):
        self.save()
        return True
    
    def cast_url(self, url):
        self.settings.last_url = url
        self.save()
        if not url:
            return

        ydl_opts = {"format": "best"}
        try:
            with FixedYoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except youtube_dl.utils.YoutubeDLError as e:
            print(e)
            Snackbar(text=f"Exception: {e}").open()
            
        codecs = ("vp8", "avc") if self.cast.model_name == "Chromecast" else CODECS  # TODO match https://developers.google.com/cast/docs/media
        cast_url = info["url"]
        mime = format_mime(info)
        if info["vcodec"] != "none":
            best_height = max(f["height"] for f in info["formats"] if any(c.startswith(f["vcodec"]) for c in codecs))
            if info["height"] < best_height:
                try:
                    mpd = build_mpd(info, CORS_PROXY, codecs, self.max_resolution)
                    mime = "application/dash+xml"
                    cast_url = f"http://{self.cast.socket_client.socket.getsockname()[0]}:{PORT}/mpd"
                    self.serve_files["mpd"] = (mpd, mime)
                except Exception as e:
                    print(e)
                    Snackbar(text=f"MPD exception, fallback to URL: {e}")
        
        title = info["title"]
        toast("Casting: " + title)
        self.cast.media_controller.play_media(cast_url, mime, title)

    def save(self):
        store.put(Settings.key, settings=self.settings)

    def switch_theme_style(self):
        self.theme_cls.theme_style = self.settings.theme = \
            "Light" if self.settings.theme == "Dark" else "Dark"

    def show_select_dialog(self):
        if not self.cast_dialog:
            self.cast_dialog = MDDialog(title="Select Chromecast", type="simple", on_dismiss=self.cast_dialog_dismiss)
        if self.cast_dialog_items:
            update_dialog_items(self.cast_dialog, self.cast_dialog_items)
        self.cast_dialog.open()
        if not self.browser:
            self.browser = pychromecast.start_discovery(self.cast_listener, self.zconf)

    def select_cast(self, device):
        print(device)
        if self.cast_dialog:
            self.cast_dialog.dismiss()
        if self.cast:
            if self.cast.device.uuid == device[1]:
                print("already connected")
                return
            else:
                self.set_cast_icon(False)
                self.cast.media_controller.unregister_status_listener(self)
                self.cast.unregister_status_listener(self)
                self.cast.disconnect()
        self.cast_status = self.media_status = None

        self.cast = pychromecast.get_chromecast_from_service(device, self.zconf)
        self.cast.media_controller.register_status_listener(self)
        self.cast.register_status_listener(self)
        self.cast.start()

        self.first_connect = True
        self.settings.last_uuid = self.cast.uuid
        self.save()

        self.update_state()

    def cast_dialog_dismiss(self, *args):
        print("dismissed dialog")
        pychromecast.stop_discovery(self.browser)
        self.browser = None
        
    def new_media_status(self, status):
        self.media_status = status
        self.update_state()
        print("media status", status)

    def new_cast_status(self, status):
        if self.cast_status is None:
            self.set_cast_icon(True)
            # initial connect
        self.cast_status = status
        self.update_state()
        print("cast status", status)
        
    def mute(self):
        self.cast.set_volume_muted(not self.cast_status.volume_muted)     
        
    def set_volume(self, volume):
        self.cast.set_volume(volume/100)
        
    def play_pause(self, *args):
        if self.is_playing:
            self.cast.media_controller.pause()
        else:
            self.cast.media_controller.play()
            
    def stop_button(self):
        self.cast.media_controller.stop()
        
    def seek(self, pos):
        self.cast.media_controller.seek(pos)
        
    def set_rate(self, rate):
        self.cast.media_controller.set_playback_rate(rate)

    def update_state(self):
        if self.cast:
            status_text = f"Connection: {self.cast.name} ({self.cast.model_name})"
        else:
            status_text = "No Connection"

        ids = self.screen.ids
        play_button = ids.play_button
        stop_button = ids.stop_button
        seek_slider = ids.seek_slider
        time_label = ids.time_label
        mute_button = ids.mute_button
        volume_slider = ids.volume_slider
        rate_slider = ids.rate_slider
        rate_dropdown = ids.rate_dropdown

        if cs := self.cast_status:
            status_text += f"""
Volume: {round(cs.volume_level*100)}%{' (muted)' * cs.volume_muted}
display_name: {cs.display_name}
status_text: {cs.status_text}
is_stand_by: {cs.is_stand_by}
is_active_input: {cs.is_active_input}"""
            mute_button.icon = ("volume-mute" if cs.volume_muted else
                                "volume-high" if cs.volume_level > 0.66 else
                                "volume-medium" if cs.volume_level > 0.33 else
                                "volume-low")
            if not volume_slider.active:
                volume_slider.value = cs.volume_level * 100
            mute_button.disabled = False
            volume_slider.disabled = False
        else:
            mute_button.disabled = True
            volume_slider.disabled = True
        if ms := self.media_status:
            status_text += f"""
title: {ms.title}
subtitle: {0}
supports:{' pause' * ms.supports_pause + ' seek' * ms.supports_seek + ' playback_rate' * ms.supports_playback_rate}
time: {ms.adjusted_current_time}/{ms.duration}
rate: {ms.playback_rate}
player_state: {ms.player_state}
supports:{' pause' * ms.supports_pause + ' seek' * ms.supports_seek + ' playback_rate' * ms.supports_playback_rate}"""

            self.is_playing = ms.player_state != MEDIA_PLAYER_STATE_PAUSED
            play_button.icon = ["play", "pause"][self.is_playing]
            play_button.disabled = not ms.supports_pause

            seek_slider.max = int(max(ms.adjusted_current_time, ms.duration or 0))
            if not seek_slider.active:
                seek_slider.value = int(ms.adjusted_current_time)

            seek_slider.disabled = not ms.supports_seek
            #time_label.text_size = None, None
            time_label.text = f"{self.format_time(ms.adjusted_current_time)} / {self.format_time(ms.duration) if ms.duration else '-'}  •  {ms.title}"
            stop_button.disabled = False

            if not rate_slider.active and ms.playback_rate > 0:
                rate_slider.value = ms.playback_rate
                rate_dropdown.text = f"{ms.playback_rate:.2f}".rstrip("0").rstrip(".") + "x"
            rate_slider.disabled = rate_dropdown.disabled = not ms.supports_playback_rate
        else:
            play_button.icon = "play"
            play_button.disabled = True
            stop_button.disabled = True
            seek_slider.disabled = True
            rate_slider.disabled = True
            rate_dropdown.disabled = True
            # time_label.text = "-/-"
        
        self.screen.ids.status_label.text = status_text

    def set_cast_icon(self, connected):
        self.screen.ids.toolbar.ids.right_actions.children[1].icon = "cast" + "-connected" * connected


if __name__ == "__main__":
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # disable red dots on right click
    store = DictStore("cast_remote.pickle")  # TODO path for android
    if not store.exists(Settings.key):
        store.put(Settings.key, settings=Settings())
    CastRemoteApp().run()
