import sys
import os
import json
import argparse
import winshell
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QSystemTrayIcon, QMenu, QListWidgetItem
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QTranslator, QLocale
from ui_mainwindow import Ui_SteamShine
from acf_parser import ACFParser
from color_utils import set_frame_color_based_on_window
from steam_process_manager import exit_game, monitor_steam_process


class MainWindow(QMainWindow):
    CONFIG_PATH = os.path.join(os.getenv("APPDATA"), "Steamshine", "config.json")

    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_SteamShine()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon("icons/icon.png"))
        self.setFixedSize(self.size())
        self.setup_frame_color()
        self.init_app_list = True
        self.force_update = False
        self.load_settings()
        self.check_startup_shortcut()
        self.create_tray_icon()
        self.init_ui_connections()
        self.create_parse_timer()

    def setup_frame_color(self):
        set_frame_color_based_on_window(self, self.ui.settingsFrame)
        set_frame_color_based_on_window(self, self.ui.pathFrame)

    def create_parse_timer(self):
        self.parse_timer = QTimer(self)
        self.parse_timer.timeout.connect(self.update_apps_json)
        self.parse_timer.setInterval(self.ui.timerSpinbox.value() * 1000)
        self.parse_timer.start()

    def init_ui_connections(self):
        self.ui.appBrowseButton.clicked.connect(self.browse_apps_json)
        self.ui.steamappsBrowseButton.clicked.connect(self.browse_steam_library)
        self.ui.timerSpinbox.valueChanged.connect(self.on_timerSpinBox_valueChanged)
        self.ui.startCheckBox.stateChanged.connect(self.on_startCheckBox_stateChanged)
        self.ui.startupCheckBox.stateChanged.connect(self.on_startupCheckBox_stateChanged)

    def on_advancedCheckBox_stateChanged(self):
        self.force_update = True
        self.update_apps_json()
        self.save_settings()

    def on_startupCheckBox_stateChanged(self):
        if self.ui.startupCheckBox.isChecked():
            self.create_startup_shortcut()
        else:
            self.delete_startup_shortcut()

    def on_startCheckBox_stateChanged(self):
        if self.ui.startCheckBox.isChecked():
            self.update_apps_json()
        self.save_settings()

    def on_timerSpinBox_valueChanged(self):
        self.parse_timer.setInterval(self.ui.timerSpinbox.value() * 1000)
        self.save_settings()

    def create_tray_icon(self):
        tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(QIcon("icons/icon.png"))
        tray_icon.setVisible(True)

        tray_menu = QMenu()
        settings_action = QAction(self.tr("Settings"), self)
        quit_action = QAction(self.tr("Quit"), self)

        tray_menu.addAction(settings_action)
        tray_menu.addAction(quit_action)
        tray_icon.setContextMenu(tray_menu)

        tray_icon.setToolTip("SteamShine")

        settings_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def browse_apps_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open apps.json", "", "JSON Files (*.json);;All Files (*)")

        if file_path:
            self.ui.appLineEdit.setText(file_path)

        self.save_settings()

    def browse_steam_library(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", "")

        if folder_path:
            self.ui.steamappsLineEdit.setText(folder_path)

        self.save_settings()

    def save_settings(self):
        config = {
            "apps_json_path": self.ui.appLineEdit.text(),
            "steam_library_path": self.ui.steamappsLineEdit.text(),
            "check_interval": self.ui.timerSpinbox.value(),
            "start": self.ui.startCheckBox.isChecked(),
            "advanced": self.ui.advancedCheckBox.isChecked(),
        }
        os.makedirs(os.path.dirname(self.CONFIG_PATH), exist_ok=True)
        with open(self.CONFIG_PATH, "w") as config_file:
            json.dump(config, config_file, indent=4)

    def load_settings(self):
        if os.path.exists(self.CONFIG_PATH):
            with open(self.CONFIG_PATH, "r") as config_file:
                config = json.load(config_file)
                self.ui.appLineEdit.setText(config.get("apps_json_path", ""))
                self.ui.steamappsLineEdit.setText(config.get("steam_library_path", ""))
                self.ui.timerSpinbox.setValue(config.get("check_interval", 10))
                self.ui.startCheckBox.setChecked(config.get("start", False))
                self.ui.advancedCheckBox.setChecked(config.get("advanced", False))
        else:
            self.show()

    def update_apps_json(self):
        steam_apps_directory = self.ui.steamappsLineEdit.text()
        apps_json_path = self.ui.appLineEdit.text()
        if not steam_apps_directory or not apps_json_path or not self.ui.startCheckBox.isChecked():
            return

        parser = ACFParser(steam_apps_directory)
        games = parser.get_steam_games()
        working_dir = os.path.abspath(sys.executable)
        executable = os.path.abspath(sys.executable)

        new_apps = {}
        if self.ui.advancedCheckBox.isChecked():
            for game in games:
                app_id = game["appid"]
                app_name = game["name"]
                new_apps[app_name] = {
                    "name": app_name,
                    "cmd": f'cmd /c ""{executable}" --monitor-process "{app_id}""',
                    "working-dir": working_dir,
                    "prep-cmd": [{"do": "", "undo": f'cmd /c ""{executable}" --exit-game"', "elevated": "false"}],
                }
        else:
            for game in games:
                app_id = game["appid"]
                app_name = game["name"]
                new_apps[app_name] = {"name": app_name, "detached": [f"steam://rungameid/{app_id}"]}

        if not os.path.exists(apps_json_path):
            with open(apps_json_path, "w") as apps_file:
                json.dump({"env": {}, "apps": []}, apps_file, indent=4)

        with open(apps_json_path, "r") as apps_file:
            old_data = json.load(apps_file)

        existing_entries = old_data.get("apps", [])
        preserved_entries = [entry for entry in existing_entries if "name" in entry and entry["name"] not in new_apps]
        preserved_entries_dict = {entry["name"]: entry for entry in preserved_entries}
        preserved_entries_dict.update(new_apps)
        sorted_managed_apps = sorted(preserved_entries_dict.values(), key=lambda x: x["name"])
        new_data = {"env": old_data.get("env", {}), "apps": sorted_managed_apps}

        with open(apps_json_path, "w") as apps_file:
            json.dump(new_data, apps_file, indent=4)
            print("apps.json updated with changes")

        self.update_game_list_widget(sorted_managed_apps)
        self.init_app_list = False
        self.force_update = False

    def update_game_list_widget(self, managed_games):
        self.ui.gameListWidget.clear()

        for game in managed_games:
            item = QListWidgetItem(game["name"])
            self.ui.gameListWidget.addItem(item)

    def create_startup_shortcut(self):
        target = sys.executable
        start_dir = os.path.dirname(target)
        shortcut_path = os.path.join(winshell.startup(), "SteamShine.lnk")

        winshell.CreateShortcut(
            Path=shortcut_path, Target=target, StartIn=start_dir, Icon=(target, 0), Description="SteamShine"
        )

    def delete_startup_shortcut(self):
        shortcut_path = os.path.join(winshell.startup(), "SteamShine.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)

    def check_startup_shortcut(self):
        shortcut_path = os.path.join(winshell.startup(), "SteamShine.lnk")
        self.ui.startupCheckBox.setChecked(os.path.exists(shortcut_path))


def main():
    # These arguments are used by SteamShine itself.
    parser = argparse.ArgumentParser(description="SteamShine Application")
    parser.add_argument("--exit-game", action="store_true")
    parser.add_argument("--monitor-process", type=str)
    args = parser.parse_args()

    if args.exit_game:
        exit_game()
    elif args.monitor_process:
        monitor_steam_process(args.monitor_process)
    else:
        app = QApplication(sys.argv)
        translator = QTranslator()
        locale_name = QLocale.system().name()
        locale = locale_name[:2]
        if locale:
            file_name = f"tr/steamshine_{locale}.qm"
        else:
            file_name = None

        if file_name and translator.load(file_name):
            app.installTranslator(translator)

        app.setStyle("Fusion")
        window = MainWindow()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
