import os
import re

# Configuración
DIRECTORIO = r"G:\\Vuze\\NINJA SCROLL (1993-2003) - Complete Movie and Anime TV Series - 1080p DUAL AUDIO x264\\Ninja Scroll The Series (2003)"
SEASON = 1
DRY_RUN = False  # Cambia a False para aplicar cambios

pattern = re.compile(r"^(\d{1,3})\s+(.*)$")

def format_episode_number(ep_num: int) -> str:
    return f"S{SEASON:02d}E{ep_num:02d}"

def rename_files():
    for filename in os.listdir(DIRECTORIO):
        filepath = os.path.join(DIRECTORIO, filename)

        if not os.path.isfile(filepath):
            continue

        name, ext = os.path.splitext(filename)

        match = pattern.match(name)
        if not match:
            print(f"SKIP (no match): {filename}")
            continue

        ep_number = int(match.group(1))
        rest_name = match.group(2)

        new_name = f"{format_episode_number(ep_number)} {rest_name}{ext}"
        new_path = os.path.join(DIRECTORIO, new_name)

        if os.path.exists(new_path):
            print(f"SKIP (exists): {new_name}")
            continue

        print(f"{filename}  →  {new_name}")

        if not DRY_RUN:
            os.rename(filepath, new_path)

if __name__ == "__main__":
    rename_files()
    
    
    
