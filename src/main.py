import argparse
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QLocale, QTranslator
from steam_process_manager import exit_game, monitor_steam_process
from steamshine import MainWindow


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
