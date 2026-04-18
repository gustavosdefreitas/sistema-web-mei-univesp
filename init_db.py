"""
init_db.py — Inicializa o banco de dados com o schema completo e dados de exemplo.

Uso:
    python init_db.py

O banco é criado em DATABASE_URL (padrão: estoque.db).
Defina DATABASE_URL no arquivo .env para usar outro caminho.
"""

import sqlite3
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "estoque.db")

conn = sqlite3.connect(DATABASE_URL)
cursor = conn.cursor()

# -------------------------------------------------------------------
# TABELAS
# -------------------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL UNIQUE,
    nome_completo TEXT,
    cpf        TEXT,
    password   TEXT    NOT NULL,
    session_id TEXT,
    perfil     TEXT    NOT NULL DEFAULT 'operador'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS empresas (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_fantasia         TEXT    NOT NULL,
    razao_social          TEXT,
    cnpj                  TEXT,
    telefone              TEXT,
    email                 TEXT,
    situacao_cadastral    TEXT,
    data_situacao_cadastral TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS fornecedores (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                  TEXT NOT NULL,
    cnpj                  TEXT,
    telefone              TEXT,
    email                 TEXT,
    situacao_cadastral    TEXT,
    data_situacao_cadastral TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    quantidade    INTEGER NOT NULL DEFAULT 0,
    preco         REAL    NOT NULL,
    empresa_id    INTEGER REFERENCES empresas(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vendas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id     INTEGER REFERENCES produtos(id),
    quantidade     INTEGER NOT NULL,
    preco_unitario REAL    NOT NULL,
    total          REAL    NOT NULL,
    data           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------------------------------------------------------------------
# DADOS DE EXEMPLO
# -------------------------------------------------------------------

# Usuário admin — senha lida do .env (ADMIN_PASSWORD) ou padrão de dev
senha_admin = os.environ.get("ADMIN_PASSWORD", "admin123")
hash_admin = bcrypt.hashpw(senha_admin.encode(), bcrypt.gensalt()).decode()
cursor.execute(
    "INSERT OR IGNORE INTO usuarios (username, password, perfil) VALUES (?, ?, ?)",
    ("admin", hash_admin, "admin"),
)

# Empresa de exemplo
cursor.execute(
    """
    INSERT OR IGNORE INTO empresas (id, nome_fantasia, razao_social, cnpj)
    VALUES (1, 'MEI Exemplo', 'MEI Exemplo LTDA', '00.000.000/0001-00')
    """,
)

# Fornecedor de exemplo
cursor.execute(
    """
    INSERT OR IGNORE INTO fornecedores (id, nome, cnpj)
    VALUES (1, 'Distribuidora Exemplo', '11.111.111/0001-11')
    """,
)

# Produtos de exemplo
cursor.executemany(
    """
    INSERT OR IGNORE INTO produtos (id, nome, quantidade, preco, empresa_id, fornecedor_id)
    VALUES (?, ?, ?, ?, 1, 1)
    """,
    [
        (1, "Arroz 5kg",     50,  12.50),
        (2, "Feijão 1kg",    30,   8.50),
        (3, "Macarrão 500g", 25,   5.00),
        (4, "Leite 1L",      40,   4.50),
        (5, "Pão",          100,   0.50),
    ],
)

conn.commit()
conn.close()

print("✅ Banco inicializado com sucesso!")
print(f"   Arquivo: {DATABASE_URL}")
print("   Tabelas: usuarios, empresas, fornecedores, produtos, vendas")
print("   Login:   admin")
print(f"   Senha:   {'(definida via ADMIN_PASSWORD)' if os.environ.get('ADMIN_PASSWORD') else 'admin123 (padrão dev — troque em produção!)'}")
