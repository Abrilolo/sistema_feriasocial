import re

file_path = r'c:\Users\atave\Documents\GitHub\sistema_feriasocial\app\static\js\admin.js'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace literal backslash-backslash-n with single backslash-n
text = text.replace('\\\\n"', '\\n"')
text = text.replace('\\\\uFEFF', '\\uFEFF')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed the escaping issues in admin.js")
