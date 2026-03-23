import re

file_path = r'c:\Users\atave\Documents\GitHub\sistema_feriasocial\app\static\js\admin.js'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace literal \\n with \n inside the template string on line 186
text = text.replace('\\\\n`', '\\n`')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed the backtick escaping issue in admin.js")
