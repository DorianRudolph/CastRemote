from kivy.lang import Builder
from kivy.config import Config
from kivy.storage.dictstore import DictStore

from kivymd.app import MDApp

KV = '''
# kv_start
MDBoxLayout:
    orientation: "vertical"

    MDToolbar:
        title: "Cast Remote"
        right_action_items: [["brightness-6", lambda x: app.switch_theme_style()]]

    MDLabel:
        text: "Content"
        halign: "center"
# kv_end
'''


class Settings:
    key = "settings"
    
    def __init__(self):
        self.theme = "Dark"


class CastRemote(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = store.get(Settings.key)["settings"]

    def build(self):
        self.theme_cls.theme_style = self.settings.theme
        return Builder.load_string(KV)

    def on_start(self):
        pass

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


if __name__ == "__main__":
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
    store = DictStore("cast_remote.pickle")
    if not store.exists(Settings.key):
        store.put(Settings.key, settings=Settings())
    CastRemote().run()
