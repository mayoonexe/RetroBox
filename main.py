import os
from pathlib import Path

# Dipendenze Kivy (assicuratevi di averle installate se testate su PC)
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button


# ==============================================================================
# 1. CONFIGURAZIONE E IMPOSTAZIONI (ex settings.py)
# ==============================================================================

APP_NAME = "RetroBox"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FULLSCREEN = False

EMULATORS = {
    "Lemuroid": {"package": "com.swordfish.lemuroid", "name": "Lemuroid"},
    "NetherSX2": {"package": "xyz.aethersx2.android", "name": "NetherSX2 / AetherSX2"},
    "RetroArch": {"package": "com.retroarch", "name": "RetroArch"},
    "RetroArch64": {"package": "com.retroarch.a64", "name": "RetroArch 64-bit"},
    "Dolphin": {"package": "org.dolphinemu.dolphinemu", "name": "Dolphin Emulator"},
    "PPSSPP": {"package": "org.ppsspp.ppsspp", "name": "PPSSPP"},
    "Vita3K": {"package": "org.vita3k.emulator", "name": "Vita3K"},
    "RPCSX": {"package": "org.rpcsx.rpcsx", "name": "RPCSX"},
    "M64PlusFZ": {"package": "paulscode.android.mupen64plusae", "name": "Mupen64Plus FZ"},
    "DraStic": {"package": "com.dsemu.drastic", "name": "DraStic DS Emulator"},
    "Citra": {"package": "org.citra.citra_emu", "name": "Citra"}
}

CONSOLE_EMULATORS = {
    "Nintendo Entertainment System": "Lemuroid",
    "Super Nintendo": "Lemuroid",
    "Game Boy": "Lemuroid",
    "Game Boy Color": "Lemuroid",
    "Game Boy Advance": "Lemuroid",
    "Nintendo 64": "M64PlusFZ",
    "Nintendo DS": "DraStic",
    "Nintendo 3DS": "Citra",
    "GameCube": "Dolphin",
    "Wii": "Dolphin",
    "PlayStation": "Lemuroid",
    "PlayStation 2": "NetherSX2",
    "PlayStation 3": "RPCSX",
    "PSP": "PPSSPP",
    "PS Vita": "Vita3K",
    "Sega Master System": "Lemuroid",
    "Sega Mega Drive": "Lemuroid",
    "Sega Game Gear": "Lemuroid",
    "Sega Saturn": "RetroArch",
    "Sega Dreamcast": "RetroArch",
    "Atari 2600": "RetroArch",
    "Atari 5200": "RetroArch",
    "Atari 7800": "RetroArch",
    "Atari Lynx": "RetroArch",
    "PC Engine": "RetroArch",
    "TurboGrafx-16": "RetroArch",
    "Neo Geo": "RetroArch",
    "Neo Geo Pocket": "RetroArch",
    "WonderSwan": "RetroArch",
    "WonderSwan Color": "RetroArch",
    "Commodore 64": "RetroArch",
    "Arcade / MAME": "RetroArch",
}


# ==============================================================================
# 2. GESTIONE STORAGE / SAF (ex storage_manager.py)
# ==============================================================================

class StorageManager:
    REQUEST_CODE = 1001

    def __init__(self, app_instance=None):
        self.selected_folder = None
        self.selected_uri = None
        self.pending_console = None
        self.app = app_instance
        self.activity_bound = False
        self._bind_android_activity()

    @property
    def is_android(self):
        return "ANDROID_ARGUMENT" in os.environ

    def set_app(self, app):
        self.app = app
        self._bind_android_activity()

    def _bind_android_activity(self):
        if not self.is_android or self.activity_bound:
            return
        try:
            from android import activity
            activity.bind(on_activity_result=self._on_activity_result)
            self.activity_bound = True
            print("RetroBox: callback Android collegato.")
        except Exception as error:
            print(f"RetroBox: impossibile collegare il callback Android. {error}")

    def _on_activity_result(self, request_code, result_code, intent):
        print(f"RetroBox: ricevuto risultato Android. Request code: {request_code}")
        self.handle_activity_result(request_code, result_code, intent)

    def select_folder(self, console_name=None):
        self.pending_console = console_name
        print(f"RetroBox: selezione cartella per {console_name}")
        if self.is_android:
            return self._select_android_folder()
        return self._select_pc_folder()

    def _select_pc_folder(self):
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="RetroBox - Seleziona la cartella della console")
            root.destroy()

            if not folder:
                print("RetroBox: selezione annullata.")
                return None

            self.selected_folder = Path(folder)
            self.selected_uri = None
            print(f"RetroBox: cartella selezionata: {self.selected_folder}")
            return str(self.selected_folder)
        except Exception as error:
            print(f"Errore selezione cartella PC: {error}")
            return None

    def _select_android_folder(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")

            activity = PythonActivity.mActivity
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)

            activity.startActivityForResult(intent, self.REQUEST_CODE)
            return None
        except Exception as error:
            print(f"Errore apertura selettore Android: {error}")
            return None

    def handle_activity_result(self, request_code, result_code, intent):
        if request_code != self.REQUEST_CODE or intent is None:
            return False

        try:
            from jnius import autoclass
            Activity = autoclass("android.app.Activity")
            Intent = autoclass("android.content.Intent")

            if result_code != Activity.RESULT_OK:
                print("RetroBox: selezione USB annullata.")
                return False

            uri = intent.getData()
            if uri is None:
                print("RetroBox: Android non ha restituito nessuna URI.")
                return False

            uri_string = uri.toString()
            self.selected_uri = uri
            self.selected_folder = None

            try:
                read_flag = Intent.FLAG_GRANT_READ_URI_PERMISSION
                write_flag = Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                flags = intent.getFlags() & (read_flag | write_flag)

                resolver = autoclass("org.kivy.android.PythonActivity").mActivity.getContentResolver()
                if flags != 0:
                    resolver.takePersistableUriPermission(uri, flags)
                    print("Permesso USB persistente salvato.")
            except Exception as permission_error:
                print(f"Errore salvataggio permesso USB: {permission_error}")

            if self.app is not None and hasattr(self.app, 'usb_folder_selected'):
                self.app.usb_folder_selected(self.pending_console, uri_string)

            return True
        except Exception as error:
            print(f"Errore gestione cartella USB: {error}")
            return False

    def list_usb_files(self):
        if self.selected_uri is None:
            return []

        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            DocumentsContract = autoclass("android.provider.DocumentsContract")
            Document = autoclass("android.provider.DocumentsContract$Document")

            activity = PythonActivity.mActivity
            resolver = activity.getContentResolver()

            tree_uri = self.selected_uri
            tree_document_id = DocumentsContract.getTreeDocumentId(tree_uri)
            children_uri = DocumentsContract.buildChildDocumentsUriUsingTree(tree_uri, tree_document_id)

            projection = [
                Document.COLUMN_DISPLAY_NAME,
                Document.COLUMN_DOCUMENT_ID,
                Document.COLUMN_MIME_TYPE
            ]

            cursor = resolver.query(children_uri, projection, None, None, None)
            if cursor is None:
                return []

            files = []
            try:
                name_index = cursor.getColumnIndex(Document.COLUMN_DISPLAY_NAME)
                document_id_index = cursor.getColumnIndex(Document.COLUMN_DOCUMENT_ID)
                mime_index = cursor.getColumnIndex(Document.COLUMN_MIME_TYPE)

                while cursor.moveToNext():
                    name = cursor.getString(name_index)
                    document_id = cursor.getString(document_id_index)
                    mime_type = cursor.getString(mime_index)

                    document_uri = DocumentsContract.buildDocumentUriUsingTree(tree_uri, document_id)
                    is_directory = (mime_type == Document.MIME_TYPE_DIR)

                    files.append({
                        "name": name,
                        "document_id": document_id,
                        "mime_type": mime_type,
                        "uri": document_uri.toString(),
                        "is_directory": is_directory
                    })
            finally:
                cursor.close()

            return files
        except Exception as error:
            print(f"Errore lettura USB: {error}")
            return []


# ==============================================================================
# 3. LANCIATORE EMULATORI (ex emulator_launcher.py)
# ==============================================================================

class EmulatorLauncher:
    @staticmethod
    def is_android():
        return "ANDROID_ARGUMENT" in os.environ

    def launch_game(self, console_name, game_uri_or_path, mime_type="*/*"):
        emulator_key = CONSOLE_EMULATORS.get(console_name)
        if not emulator_key or emulator_key not in EMULATORS:
            print(f"Nessun emulatore configurato per: {console_name}")
            return False

        emulator_info = EMULATORS[emulator_key]
        package_name = emulator_info["package"]

        if self.is_android():
            return self._launch_android_intent(package_name, game_uri_or_path, mime_type)
        else:
            print(f"[PC] Apertura gioco {game_uri_or_path} tramite emulatore {emulator_key}")
            return True

    def _launch_android_intent(self, package_name, uri_string, mime_type):
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")

            activity = PythonActivity.mActivity
            uri = Uri.parse(uri_string)

            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, mime_type if mime_type else "*/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

            intent.setPackage(package_name)
            activity.startActivity(intent)
            return True
        except Exception as e:
            print(f"Errore nel lancio dell'Intent Android: {e}")
            return False


# ==============================================================================
# 4. APPLICAZIONE KIVY PRINCIPALE
# ==============================================================================

class RetroBoxApp(App):
    def build(self):
        self.title = APP_NAME
        self.storage_manager = StorageManager(self)
        self.emulator_launcher = EmulatorLauncher()

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.status_label = Label(
            text="RetroBox Pronto", 
            font_size='20sp'
        )
        layout.add_widget(self.status_label)

        btn_select = Button(
            text="Seleziona Cartella USB / ROMs", 
            size_hint=(1, 0.2)
        )
        btn_select.bind(on_press=self.on_select_folder_pressed)
        layout.add_widget(btn_select)

        return layout

    def on_select_folder_pressed(self, instance):
        self.storage_manager.select_folder("PlayStation 2")

    def usb_folder_selected(self, console_name, uri_string):
        self.status_label.text = f"URI Selezionato per {console_name}:\n{uri_string}"
        print(f"Callback ricevuto nell'App per {console_name}: {uri_string}")


if __name__ == '__main__':
    RetroBoxApp().run()