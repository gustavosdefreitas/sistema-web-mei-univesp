import sqlite3
import os
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL', 'estoque.db')

# Lê a senha do admin da variável de ambiente ADMIN_PASSWORD
# Defina no arquivo .env antes de executar: ADMIN_PASSWORD=sua_senha_segura
senha_admin = os.environ.get('ADMIN_PASSWORD')
if not senha_admin:
    print('❌ Erro: variável de ambiente ADMIN_PASSWORD não definida.')
    print('   Crie um arquivo .env com: ADMIN_PASSWORD=sua_senha_segura')
    exit(1)

# APAGA TUDO e recria BANCO LIMPO
conn = sqlite3.connect(DATABASE_URL)
c = conn.cursor()
c.execute('DROP TABLE IF EXISTS usuarios')
c.execute('DROP TABLE IF EXISTS produtos')
c.execute('DROP TABLE IF EXISTS vendas')

# CRIA TABELAS
c.execute('''CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    session_id TEXT,
    perfil TEXT DEFAULT "user"
)''')

c.execute('''CREATE TABLE produtos (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    quantidade INTEGER,
    preco REAL
)''')

c.execute('''CREATE TABLE vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER,
    quantidade INTEGER,
    preco_unitario REAL,
    total REAL
)''')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash_admin = pwd_context.hash(senha_admin)
c.execute('INSERT INTO usuarios (username, password, perfil) VALUES (?, ?, ?)',
          ('admin', hash_admin, 'admin'))

# PRODUTOS DE TESTE
c.executemany('INSERT OR REPLACE INTO produtos VALUES(?, ?, ?, ?)', [
    (1, 'Arroz 5kg', 50, 12.5),
    (2, 'Feijão 1kg', 30, 8.5),
    (3, 'Macarrão 500g', 25, 5.0)
])

conn.commit()
conn.close()
print('✅ SISTEMA RECRIADO!')
print('👤 Login: admin')
print('🔑 Senha definida via ADMIN_PASSWORD')
print('🎉 http://localhost:8000')
