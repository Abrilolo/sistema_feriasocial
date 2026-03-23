import os

path = r'c:\Users\atave\Documents\GitHub\sistema_feriasocial\requirements.txt'

if os.path.exists(path):
    with open(path, 'rb') as f:
        content = f.read()
    
    # Try decoding as utf-16le (common in powershell >)
    try:
        decoded = content.decode('utf-16le')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(decoded)
        print("Successfully converted requirements.txt to UTF-8")
    except Exception as e:
        print(f"Failed to convert or already UTF-8: {e}")
