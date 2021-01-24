from kivy.lang import Builder
from kivy.config import Config
from kivy.storage.dictstore import DictStore
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ObjectProperty
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.list import TwoLineIconListItem
from kivymd.uix.dialog import MDDialog

import pychromecast
import zeroconf

KV = '''
# kv_start
    
<Item>:
    on_release: app.select_cast(self.device)
    
    IconLeftWidget:
        icon: root.icon


BoxLayout:
    orientation: "vertical"
    spacing: "10dp"
    
    MDToolbar:
        title: "Cast Remote"
        id: toolbar
        right_action_items: [["cast", lambda x: app.show_select_dialog()], ["brightness-6", lambda x: app.switch_theme_style()]]
        
    ScrollView:
        
        GridLayout:
            cols: 1
            adaptive_size: True
            size_hint: 1, None
            padding: "10dp"
            spacing: "10dp"

            MDLabel:
                id: selected_cast
                text: "  Selected Chromecast: <none>"
                height: "20dp"
                size_hint_y: None

            MDRaisedButton:    
                text: "Hello"
                pos_hint: {"center_x": .5}

            MDRaisedButton:    
                text: "Hello"

            MDRaisedButton:    
                text: "Hello"

            MDRaisedButton:    
                text: "Hello"

            MDRaisedButton:    
                text: "Hello"
    
# kv_end
'''


class Item(TwoLineIconListItem):
    icon = StringProperty()
    device = ObjectProperty()


class Settings:
    key = "settings"
    theme = "Dark"
    last_cast = None
    
    
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)        
        self.settings = store.get(Settings.key)["settings"]
        self.theme_cls.theme_style = self.settings.theme
        
        self.screen = Builder.load_string(KV)

        self.cast_listener = pychromecast.CastListener(self.update_chromecast_discovery, self.update_chromecast_discovery, self.update_chromecast_discovery)
        self.zconf = zeroconf.Zeroconf()

    def update_chromecast_discovery(self, *args):
        self.cast_dialog_items = [
            Item(text=device[3], secondary_text=device[2], device=device, icon="monitor")
            for device in self.cast_listener.devices
        ]
        self.cast_dialog_items.sort(key=lambda i: i.text)
        update_dialog_items(self.cast_dialog, self.cast_dialog_items)

    def build(self):
        return self.screen

    def on_stop(self):
        self.save()

    def on_pause(self):
        self.save()
        return True

    def save(self):
        store.put(Settings.key, settings=self.settings)

    def switch_theme_style(self):
        self.theme_cls.theme_style = self.settings.theme = \
            "Light" if self.settings.theme == "Dark" else "Dark"

    def show_select_dialog(self):
        if not self.cast_dialog:
            self.cast_dialog = MDDialog(title="Select Chromecast", type="simple", on_dismiss=self.cast_dialog_dismiss)
        self.cast_dialog.open()
        self.browser = pychromecast.start_discovery(self.cast_listener, self.zconf)
        
    def select_cast(self, device):
        print(device)
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

    def cast_dialog_dismiss(self, *args):
        print("dismissed dialog")
        pychromecast.stop_discovery(self.browser)
        
    def new_media_status(self, status):
        self.media_status = status
        print("media status", status)

    def new_cast_status(self, status):
        if self.cast_status is None:
            self.set_cast_icon(True)
            # initial connect
        self.cast_status = status
        print("cast status", status)

    def set_cast_icon(self, connected):
        self.screen.ids.toolbar.ids.right_actions.children[1].icon = "cast" + "-connected" * connected


if __name__ == "__main__":
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # disable red dots on right click
    store = DictStore("cast_remote.pickle")  # TODO path for android
    if not store.exists(Settings.key):
        store.put(Settings.key, settings=Settings())
    CastRemoteApp().run()
