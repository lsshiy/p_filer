import os

def list_directory(path):
    try:
        return os.listdir(path)
    except Exception as e:
        print(f"Error listing {path}: {e}")
        return []
