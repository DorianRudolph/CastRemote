from kivy.lang import Builder
from kivy.config import Config
from kivy.storage.dictstore import DictStore
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import TwoLineIconListItem
from kivymd.uix.dialog import MDDialog

import pychromecast
import zeroconf

KV = '''
# kv_start
    
<Item>:
    on_release: print("release", self.text, self.uuid)
    IconLeftWidget:
        icon: root.icon

GridLayout:
    cols: 1
    height: self.minimum_height
    spacing: "10dp"
    
    MDToolbar:
        title: "Cast Remote"
        id: toolbar
        right_action_items: [["cast", lambda x: app.select_cast()], ["brightness-6", lambda x: app.switch_theme_style()]]
        
    MDLabel:
        id: selected_cast
        text: "  Selected Chromecast: <none>"
        height: "20dp"
        size_hint_y: None
    
    MDBoxLayout:
        size_hint_x: 1
        adaptive_height: True
        spacing: "10dp"
        padding: "10dp"
        
        MDRaisedButton:
            text: "Scan"
            icon: "refresh"
            
        MDDropDownItem:
            size_hint_x: 1
            id: cast_selector
            text: "Item 0"
            current_item: "Item 0"
            on_release: app.cast_menu.open()
            pos_hint: {"center_y": .5}

    
    MDRaisedButton:    
        text: "Hello"
        pos_hint: {"center_x": .5}
        
    MDRaisedButton:    
        text: "Hello"
    
# kv_end
'''


class Item(TwoLineIconListItem):
    icon = StringProperty()
    uuid = StringProperty()


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)        
        self.settings = store.get(Settings.key)["settings"]
        self.theme_cls.theme_style = self.settings.theme
        
        self.screen = Builder.load_string(KV)
        
        menu_items = [{"icon": "git", "text": f"Item asdfasdfasdfa {i}"} for i in range(5)]
        self.cast_menu = MDDropdownMenu(
            caller=self.screen.ids.cast_selector,
            items=menu_items,
            width_mult=4,
        )
        self.cast_menu.bind(on_release=self.set_item)

        self.cast_listener = pychromecast.CastListener(self.update_chromecast_discovery, self.update_chromecast_discovery, self.update_chromecast_discovery)
        self.zconf = zeroconf.Zeroconf()

    def update_chromecast_discovery(self, *args):
        self.cast_dialog_items = [
            Item(text=device[3], secondary_text=device[2], uuid=str(device[1]), icon="monitor")
            for device in self.cast_listener.devices
        ]
        self.cast_dialog_items.sort(key=lambda i: i.text)
        update_dialog_items(self.cast_dialog, self.cast_dialog_items)
        for device in self.cast_listener.devices:
            print(device)

    def set_item(self, instance_menu, instance_menu_item):
        self.screen.ids.cast_selector.set_item(instance_menu_item.text)
        self.cast_menu.dismiss()

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

    def select_cast(self):
        if not self.cast_dialog:
            self.cast_dialog = MDDialog(title="Select Chromecast", type="simple", on_dismiss=self.cast_dialog_dismiss)
        self.cast_dialog.open()
        self.browser = pychromecast.start_discovery(self.cast_listener, self.zconf)
        
    def cast_dialog_dismiss(self, *args):
        print("dismissed dialog")
        pychromecast.stop_discovery(self.browser)


if __name__ == "__main__":
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # disable red dots on right click
    store = DictStore("cast_remote.pickle")  # TODO path for android
    if not store.exists(Settings.key):
        store.put(Settings.key, settings=Settings())
    CastRemoteApp().run()
