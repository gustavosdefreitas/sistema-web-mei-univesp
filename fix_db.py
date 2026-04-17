# fix_db.py
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL', 'estoque.db')

conn = sqlite3.connect(DATABASE_URL)
c = conn.cursor()

# Cria coluna perfil se não existir
c.execute("PRAGMA table_info(usuarios)")
cols = [col[1] for col in c.fetchall()]
if 'perfil' not in cols:
    c.execute('ALTER TABLE usuarios ADD COLUMN perfil TEXT DEFAULT "user"')

# Admin é ADMIN
c.execute('UPDATE usuarios SET perfil = "admin" WHERE username = "admin"')
conn.commit()
conn.close()
print('✅ Coluna perfil adicionada!')
