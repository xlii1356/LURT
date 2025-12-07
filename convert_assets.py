import csv
import json
import os
import shutil
import sys

def setup_module():
    base_dir = os.path.join(os.getcwd(), 'module')
    dirs = ['scripts', 'styles', 'templates', 'assets']
    
    # Create directories
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"Created {base_dir}")
        
    for d in dirs:
        path = os.path.join(base_dir, d)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created {path}")

    # Convert CSV to JSON
    csv_path = os.path.join(os.getcwd(), 'lancer', 'lancer_reactions.csv')
    json_path = os.path.join(base_dir, 'assets', 'lancer_reactions.json')
    
    data = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Converted CSV to JSON at {json_path}")
    else:
        print(f"Error: CSV not found at {csv_path}")

    # Copy Icon (Rename to png for consistency if compatible, but just copy for now)
    # Browsers can display ICO usually, but preferred PNG. 
    # Without PIL, we just copy.
    icon_src = os.path.join(os.getcwd(), 'lurt_icon.ico')
    icon_dst = os.path.join(base_dir, 'assets', 'lurt-icon.ico')
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, icon_dst)
        print(f"Copied icon to {icon_dst}")

if __name__ == "__main__":
    setup_module()
