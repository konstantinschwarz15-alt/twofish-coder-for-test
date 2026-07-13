"""
Verwaltet die "Chats" (Abteile): pro Chat ein eigener, zufaellig erzeugter
Twofish-Schluessel. Wird als einfache JSON-Datei auf dem Geraet gespeichert.
"""
import json
import os
import uuid
import time
import secrets

KEY_SIZES = {"128 Bit": 16, "192 Bit": 24, "256 Bit": 32}


class ChatStore:
    def __init__(self, path: str):
        self.path = path
        self._data = {"chats": []}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"chats": []}

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    @property
    def chats(self):
        return self._data["chats"]

    def create_chat(self, name: str, key_size_bytes: int = 32) -> dict:
        chat = {
            "id": str(uuid.uuid4()),
            "name": name.strip() or "Unbenannter Chat",
            "key_hex": secrets.token_hex(key_size_bytes),
            "created": time.time(),
        }
        self._data["chats"].append(chat)
        self.save()
        return chat

    def regenerate_key(self, chat_id: str, key_size_bytes: int = 32):
        for chat in self._data["chats"]:
            if chat["id"] == chat_id:
                chat["key_hex"] = secrets.token_hex(key_size_bytes)
                self.save()
                return chat
        raise KeyError("Chat nicht gefunden")

    def rename_chat(self, chat_id: str, new_name: str):
        for chat in self._data["chats"]:
            if chat["id"] == chat_id:
                chat["name"] = new_name.strip() or chat["name"]
                self.save()
                return chat
        raise KeyError("Chat nicht gefunden")

    def delete_chat(self, chat_id: str):
        self._data["chats"] = [c for c in self._data["chats"] if c["id"] != chat_id]
        self.save()

    def get_chat(self, chat_id: str):
        for chat in self._data["chats"]:
            if chat["id"] == chat_id:
                return chat
        return None

    def sorted_chats(self, key: str = "name", reverse: bool = False):
        chats = list(self._data["chats"])
        if key == "name":
            chats.sort(key=lambda c: c["name"].lower(), reverse=reverse)
        elif key == "created":
            chats.sort(key=lambda c: c["created"], reverse=reverse)
        return chats
