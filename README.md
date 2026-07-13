# Twofish Chat-Verschluesselung - Android-Version (Kivy)

Gleiche Funktion wie die Windows-Version - gleicher, gepruefter
Twofish-Code (`twofish_cipher.py`, `twofish_cbc.py`, `chat_store.py`) -
nur mit einer fuer Touch-Bedienung gebauten Oberflaeche (Kivy statt Tkinter).

## Wichtiger Hinweis zur APK

**Ich kann in dieser Sandbox-Umgebung keine fertige .apk-Datei erzeugen.**
Das Bauen einer Android-APK erfordert das Android SDK, das Android NDK und
Gradle (mehrere Gigabyte an Downloads von Google-Servern), und diese Umgebung
hier hat nur eingeschraenkten Internetzugriff (u. a. auf PyPI/GitHub, aber
nicht auf die Android-Downloadserver). Deshalb kann ich den Buildozer-Schritt,
der die APK erzeugt, hier nicht ausfuehren.

Was ich stattdessen getan habe:

- Den kompletten Code geschrieben und **die komplette Verschluesselungs- und
  Programmlogik hier bereits automatisiert getestet** (unter einem virtuellen
  Display, mit simulierten Chat-Erstellungen, Verschluesseln/Entschluesseln
  und Sortieren) - alles funktioniert wie erwartet.
- Eine fertige `buildozer.spec` mitgeliefert, mit der sich aus genau diesem
  Code in wenigen Schritten eine APK bauen laesst.

## So bauen Sie selbst die APK (einmalig, ca. 15-30 Minuten)

Buildozer laeuft nur unter Linux (auf Windows z. B. ueber WSL2 mit Ubuntu).

1. Ubuntu/WSL2 oeffnen und Grundpakete installieren:
   ```
   sudo apt update
   sudo apt install -y python3-pip build-essential git python3-dev \
       ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
       libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev \
       openjdk-17-jdk unzip
   pip install --user buildozer cython
   ```
2. Diesen Ordner (mit `main.py`, `twofish_cipher.py`, `twofish_cbc.py`,
   `chat_store.py`, `buildozer.spec`) auf den Linux-Rechner/WSL kopieren.
3. Im Ordner ausfuehren:
   ```
   buildozer -v android debug
   ```
   Buildozer laedt beim ersten Lauf automatisch Android SDK/NDK herunter
   (mehrere GB) und baut danach die APK.
4. Die fertige Datei liegt danach unter `bin/twofishchat-1.0-arm64-v8a_armeabi-v7a-debug.apk`
   und kann auf ein Android-Geraet uebertragen und installiert werden
   (in den Android-Einstellungen muss ggf. "Installation aus unbekannten
   Quellen" erlaubt werden).

## Vorher am PC ausprobieren (ohne Android)

Da der Code reines Kivy ist, laeuft er auch direkt auf dem PC/Mac/Linux, um
die Bedienung vorab zu testen - ganz ohne APK-Build:

```
pip install kivy
python main.py
```

## Alternative ohne eigenen Linux-Rechner

Wer kein Linux/WSL einrichten moechte, kann denselben Ordner auch in einer
kostenlosen Cloud-Build-Umgebung bauen lassen, z. B.:

- GitHub Actions mit einer vorgefertigten "buildozer-action" (Suche auf
  GitHub nach "buildozer-action"), die bei jedem Push automatisch eine APK
  als Download-Artefakt erzeugt.

## Sicherheitshinweis

Siehe README der Windows-Version - dieselben Hinweise gelten hier: Twofish
selbst ist solide, aber die Schluessel liegen unverschluesselt in der
App-Datenablage, und es gibt keine zusaetzliche Integritaetspruefung (MAC).
