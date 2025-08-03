import os

folder_path = r'2018-19\Extracted'  # ← replace this with your folder path

for filename in os.listdir(folder_path):
    if len(filename) >= 2:
        old_path = os.path.join(folder_path, filename)
        new_filename = '2018-19' + filename[2:]
        new_path = os.path.join(folder_path, new_filename)
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} → {new_filename}")
