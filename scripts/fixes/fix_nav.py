import re

file_path = r'c:\Users\atave\Documents\GitHub\sistema_feriasocial\app\templates\base.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the entire <nav class="nav">...</nav> block
new_nav = """    <nav class="nav">
      <a href="/login" id="navLogin">Login</a>
      <a href="#" id="logoutBtn" class="nav-logout" style="display: none;">Salir</a>
    </nav>"""

# Using regex to replace the nav section
pattern = r'<nav class="nav">.*?</nav>'
# re.DOTALL is needed to match across multiple lines
new_content = re.sub(pattern, new_nav, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully updated base.html navigation")
