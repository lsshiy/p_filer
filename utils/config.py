import json
import os
import sys

class ConfigManager:
    def __init__(self, filename="session.json"):
        # Save in the same directory as the executable/script for simplicity, 
        # or user app data. For now, local dir is fine.
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.filepath = os.path.join(base_path, filename)

    def save_session(self, cards_state):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({"cards": cards_state}, f, indent=4)
        except Exception as e:
            print(f"Error saving session: {e}")

    def load_session(self):
        if not os.path.exists(self.filepath):
            return None
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session: {e}")
            return None
