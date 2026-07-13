# -*- coding: utf-8 -*-
"""
Twofish Chat-Verschluesselung - Android App (Kivy)
====================================================
Gleiche Funktion wie die Windows-Version: pro Chat/Abteil ein eigener,
zufaellig erzeugter Twofish-Schluessel, Texte lassen sich damit ver- und
entschluesseln. Reines Python, keine C-Abhaengigkeiten -> laesst sich mit
Buildozer zu einer APK packen.
"""
import os
import time

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.core.clipboard import Clipboard

from chat_store import ChatStore, KEY_SIZES
from twofish_cbc import encrypt_text, decrypt_text


def data_dir():
    try:
        return App.get_running_app().user_data_dir
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".twofish_chat_app")


class NewChatPopup(Popup):
    def __init__(self, on_confirm, **kwargs):
        super().__init__(title="Neuer Chat", size_hint=(0.9, 0.5), **kwargs)
        self.on_confirm = on_confirm
        layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        layout.add_widget(Label(text="Name des Chats:", size_hint_y=None, height=dp(24)))
        self.name_input = TextInput(multiline=False, size_hint_y=None, height=dp(40))
        layout.add_widget(self.name_input)
        layout.add_widget(Label(text="Schluesselgroesse:", size_hint_y=None, height=dp(24)))
        self.size_spinner = Spinner(text="256 Bit", values=list(KEY_SIZES.keys()),
                                     size_hint_y=None, height=dp(40))
        layout.add_widget(self.size_spinner)
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel_btn = Button(text="Abbrechen")
        cancel_btn.bind(on_release=lambda *_: self.dismiss())
        ok_btn = Button(text="Erstellen")
        ok_btn.bind(on_release=self._confirm)
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(ok_btn)
        layout.add_widget(btn_row)
        self.content = layout

    def _confirm(self, *_):
        name = self.name_input.text.strip() or "Unbenannter Chat"
        size_label = self.size_spinner.text
        self.dismiss()
        self.on_confirm(name, size_label)


def info_popup(title, message):
    content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    content.add_widget(Label(text=message))
    btn = Button(text="OK", size_hint_y=None, height=dp(44))
    content.add_widget(btn)
    popup = Popup(title=title, content=content, size_hint=(0.9, 0.4))
    btn.bind(on_release=popup.dismiss)
    popup.open()
    return popup


def confirm_popup(title, message, on_yes):
    content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    content.add_widget(Label(text=message))
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    no_btn = Button(text="Abbrechen")
    yes_btn = Button(text="Ja, fortfahren")
    row.add_widget(no_btn)
    row.add_widget(yes_btn)
    content.add_widget(row)
    popup = Popup(title=title, content=content, size_hint=(0.9, 0.45))
    no_btn.bind(on_release=popup.dismiss)

    def _yes(*_):
        popup.dismiss()
        on_yes()

    yes_btn.bind(on_release=_yes)
    popup.open()


class RootLayout(BoxLayout):
    pass


class TwofishApp(App):
    title = "Twofish Chat"

    def build(self):
        os.makedirs(data_dir(), exist_ok=True)
        self.store = ChatStore(os.path.join(data_dir(), "chats.json"))
        self.selected_chat_id = None
        self.sort_key = "name"
        self.sort_reverse = False

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        # --- chat selector row -------------------------------------------------
        chat_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.chat_spinner = Spinner(text="(kein Chat)", values=[])
        self.chat_spinner.bind(text=self._on_chat_selected)
        chat_row.add_widget(self.chat_spinner)
        new_btn = Button(text="+ Neu", size_hint_x=None, width=dp(70))
        new_btn.bind(on_release=lambda *_: self._open_new_chat_popup())
        chat_row.add_widget(new_btn)
        sort_btn = Button(text="Sortieren", size_hint_x=None, width=dp(90))
        sort_btn.bind(on_release=lambda *_: self._toggle_sort())
        chat_row.add_widget(sort_btn)
        del_btn = Button(text="Loeschen", size_hint_x=None, width=dp(90))
        del_btn.bind(on_release=lambda *_: self._delete_current_chat())
        chat_row.add_widget(del_btn)
        root.add_widget(chat_row)

        # --- key row -------------------------------------------------------
        key_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.key_label = TextInput(text="-", readonly=True, multiline=False, font_size=dp(12))
        key_row.add_widget(self.key_label)
        copy_key_btn = Button(text="Kopieren", size_hint_x=None, width=dp(90))
        copy_key_btn.bind(on_release=lambda *_: self._copy_key())
        key_row.add_widget(copy_key_btn)
        regen_btn = Button(text="Neu erzeugen", size_hint_x=None, width=dp(110))
        regen_btn.bind(on_release=lambda *_: self._regen_key())
        key_row.add_widget(regen_btn)
        root.add_widget(key_row)

        scroll = ScrollView()
        body = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        body.bind(minimum_height=body.setter("height"))

        body.add_widget(Label(text="Klartext eingeben:", size_hint_y=None, height=dp(24),
                               halign="left", valign="middle"))
        self.plain_in = TextInput(multiline=True, size_hint_y=None, height=dp(100))
        body.add_widget(self.plain_in)
        enc_btn = Button(text="Verschluesseln", size_hint_y=None, height=dp(46))
        enc_btn.bind(on_release=lambda *_: self._do_encrypt())
        body.add_widget(enc_btn)
        self.enc_out = TextInput(multiline=True, readonly=True, size_hint_y=None, height=dp(100),
                                  font_size=dp(12))
        body.add_widget(self.enc_out)
        copy_enc_btn = Button(text="Verschluesselten Text kopieren", size_hint_y=None, height=dp(40))
        copy_enc_btn.bind(on_release=lambda *_: self._copy(self.enc_out.text))
        body.add_widget(copy_enc_btn)

        body.add_widget(Label(text="Verschluesselten Text einfuegen:", size_hint_y=None,
                               height=dp(24)))
        self.cipher_in = TextInput(multiline=True, size_hint_y=None, height=dp(100), font_size=dp(12))
        body.add_widget(self.cipher_in)
        dec_btn = Button(text="Entschluesseln", size_hint_y=None, height=dp(46))
        dec_btn.bind(on_release=lambda *_: self._do_decrypt())
        body.add_widget(dec_btn)
        self.plain_out = TextInput(multiline=True, readonly=True, size_hint_y=None, height=dp(100))
        body.add_widget(self.plain_out)

        scroll.add_widget(body)
        root.add_widget(scroll)

        self._refresh_chat_spinner()
        return root

    # ------------------------------------------------------------- helpers
    def _refresh_chat_spinner(self, select_id=None):
        chats = self.store.sorted_chats(self.sort_key, self.sort_reverse)
        self._chat_lookup = {c["name"]: c["id"] for c in chats}
        self.chat_spinner.values = [c["name"] for c in chats] or ["(kein Chat)"]
        target_id = select_id or self.selected_chat_id
        target_chat = self.store.get_chat(target_id) if target_id else None
        if target_chat:
            self.chat_spinner.text = target_chat["name"]
        elif chats:
            self.chat_spinner.text = chats[0]["name"]
            self.selected_chat_id = chats[0]["id"]
        else:
            self.chat_spinner.text = "(kein Chat)"
            self.selected_chat_id = None
        self._update_key_label()

    def _on_chat_selected(self, spinner, text):
        chat_id = self._chat_lookup.get(text)
        if chat_id:
            self.selected_chat_id = chat_id
        self._update_key_label()

    def _update_key_label(self):
        chat = self.store.get_chat(self.selected_chat_id) if self.selected_chat_id else None
        self.key_label.text = chat["key_hex"] if chat else "-"

    def _toggle_sort(self):
        if self.sort_key == "name":
            self.sort_key = "created"
        else:
            self.sort_key = "name"
        self.sort_reverse = not self.sort_reverse
        self._refresh_chat_spinner()

    def _open_new_chat_popup(self):
        NewChatPopup(on_confirm=self._create_chat).open()

    def _create_chat(self, name, size_label):
        chat = self.store.create_chat(name, KEY_SIZES[size_label])
        self._refresh_chat_spinner(select_id=chat["id"])

    def _delete_current_chat(self):
        chat = self.store.get_chat(self.selected_chat_id) if self.selected_chat_id else None
        if not chat:
            info_popup("Hinweis", "Bitte zuerst einen Chat auswaehlen.")
            return

        def do_delete():
            self.store.delete_chat(chat["id"])
            self.selected_chat_id = None
            self._refresh_chat_spinner()

        confirm_popup("Loeschen bestaetigen",
                       f"Chat '{chat['name']}' und seinen Schluessel wirklich loeschen?",
                       do_delete)

    def _regen_key(self):
        chat = self.store.get_chat(self.selected_chat_id) if self.selected_chat_id else None
        if not chat:
            info_popup("Hinweis", "Bitte zuerst einen Chat auswaehlen.")
            return

        def do_regen():
            self.store.regenerate_key(chat["id"], 32)
            self._update_key_label()

        confirm_popup("Neuen Schluessel erzeugen",
                       "Alte, damit verschluesselte Texte werden dann unlesbar. Fortfahren?",
                       do_regen)

    def _copy_key(self):
        chat = self.store.get_chat(self.selected_chat_id) if self.selected_chat_id else None
        if chat:
            Clipboard.copy(chat["key_hex"])

    def _copy(self, text):
        if text:
            Clipboard.copy(text)

    def _do_encrypt(self):
        chat = self.store.get_chat(self.selected_chat_id) if self.selected_chat_id else None
        if not chat:
            info_popup("Hinweis", "Bitte zuerst einen Chat auswaehlen oder anlegen.")
            return
        plaintext = self.plain_in.text
        if not plaintext:
            return
        key = bytes.fromhex(chat["key_hex"])
        try:
            self.enc_out.text = encrypt_text(key, plaintext)
        except Exception as exc:
            info_popup("Fehler", str(exc))

    def _do_decrypt(self):
        chat = self.store.get_chat(self.selected_chat_id) if self.selected_chat_id else None
        if not chat:
            info_popup("Hinweis", "Bitte zuerst den passenden Chat auswaehlen.")
            return
        ciphertext = self.cipher_in.text.strip()
        if not ciphertext:
            return
        key = bytes.fromhex(chat["key_hex"])
        try:
            self.plain_out.text = decrypt_text(key, ciphertext)
        except Exception as exc:
            info_popup("Entschluesselung fehlgeschlagen", str(exc))


if __name__ == "__main__":
    TwofishApp().run()
