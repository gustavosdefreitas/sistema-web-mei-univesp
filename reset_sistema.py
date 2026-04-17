"""
reset_sistema.py — Apaga e recria o banco do zero com dados de exemplo.

⚠️  ATENÇÃO: todos os dados existentes serão PERDIDOS.

Uso:
    ADMIN_PASSWORD=sua_senha python reset_sistema.py
    # ou defina ADMIN_PASSWORD no arquivo .env
"""

import sqlite3
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "estoque.db")

senha_admin = os.environ.get("ADMIN_PASSWORD")
if not senha_admin:
    print("❌ Erro: variável de ambiente ADMIN_PASSWORD não definida.")
    print("   Crie um arquivo .env com: ADMIN_PASSWORD=sua_senha_segura")
    exit(1)

conn = sqlite3.connect(DATABASE_URL)
c = conn.cursor()

# -------------------------------------------------------------------
# APAGA TUDO
# -------------------------------------------------------------------
c.execute("DROP TABLE IF EXISTS vendas")
c.execute("DROP TABLE IF EXISTS produtos")
c.execute("DROP TABLE IF EXISTS fornecedores")
c.execute("DROP TABLE IF EXISTS empresas")
c.execute("DROP TABLE IF EXISTS usuarios")

# -------------------------------------------------------------------
# RECRIA TABELAS
# -------------------------------------------------------------------
c.execute("""
CREATE TABLE usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,
    session_id TEXT,
    perfil     TEXT    NOT NULL DEFAULT 'user'
)
""")

c.execute("""
CREATE TABLE empresas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_fantasia TEXT    NOT NULL,
    razao_social  TEXT,
    cnpj          TEXT,
    telefone      TEXT,
    email         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
CREATE TABLE fornecedores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    cnpj       TEXT,
    telefone   TEXT,
    email      TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
CREATE TABLE produtos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    quantidade    INTEGER NOT NULL DEFAULT 0,
    preco         REAL    NOT NULL,
    empresa_id    INTEGER REFERENCES empresas(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
CREATE TABLE vendas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id     INTEGER REFERENCES produtos(id),
    quantidade     INTEGER NOT NULL,
    preco_unitario REAL    NOT NULL,
    total          REAL    NOT NULL,
    data           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------------------------------------------------------------------
# DADOS INICIAIS
# -------------------------------------------------------------------
hash_admin = bcrypt.hashpw(senha_admin.encode(), bcrypt.gensalt()).decode()
c.execute(
    "INSERT INTO usuarios (username, password, perfil) VALUES (?, ?, ?)",
    ("admin", hash_admin, "admin"),
)

c.execute(
    """
    INSERT INTO empresas (id, nome_fantasia, razao_social, cnpj)
    VALUES (1, 'MEI Exemplo', 'MEI Exemplo LTDA', '00.000.000/0001-00')
    """,
)

c.execute(
    """
    INSERT INTO fornecedores (id, nome, cnpj)
    VALUES (1, 'Distribuidora Exemplo', '11.111.111/0001-11')
    """,
)

c.executemany(
    """
    INSERT INTO produtos (nome, quantidade, preco, empresa_id, fornecedor_id)
    VALUES (?, ?, ?, 1, 1)
    """,
    [
        ("Arroz 5kg",     50,  12.50),
        ("Feijão 1kg",    30,   8.50),
        ("Macarrão 500g", 25,   5.00),
        ("Leite 1L",      40,   4.50),
        ("Pão",          100,   0.50),
    ],
)

conn.commit()
conn.close()

print("✅ Sistema recriado com sucesso!")
print(f"   Arquivo: {DATABASE_URL}")
print("   Login:   admin")
print("   Senha:   (definida via ADMIN_PASSWORD)")
print("   🌐 http://localhost:8000")
