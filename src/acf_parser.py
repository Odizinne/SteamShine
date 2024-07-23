import os
import re

class ACFParser:
    def __init__(self, steam_apps_directory):
        self.steam_apps_directory = steam_apps_directory

    def parse_acf(self, acf_content):
        """Parses ACF file content and returns a dictionary."""
        pattern = r'\"(.*?)\"\s*\"(.*?)\"'
        parsed_data = dict(re.findall(pattern, acf_content))
        return parsed_data

    def get_steam_games(self):
        """Reads ACF files from the Steam library directory and extracts game info."""
        games = []
        if not os.path.exists(self.steam_apps_directory):
            print("Directory does not exist:", self.steam_apps_directory)
            return games

        for root, _, files in os.walk(self.steam_apps_directory):
            for file in files:
                if file.endswith('.acf'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        acf_content = f.read()
                        game_info = self.parse_acf(acf_content)
                        if 'appid' in game_info and 'name' in game_info:
                            if game_info['name'] != "Steamworks Common Redistributables":
                                games.append({
                                    'appid': game_info['appid'],
                                    'name': game_info['name']
                                })
        return games
