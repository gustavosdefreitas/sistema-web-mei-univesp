import pytest
import sqlite3
from fastapi.testclient import TestClient
from main import app, get_db, hash_password

# ---------------------------------------------------------------------------
# Banco de dados em memória para os testes
# ---------------------------------------------------------------------------

def create_test_db():
    """Cria um banco SQLite em memória com o schema completo e dados de seed."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome_completo TEXT,
            cpf TEXT,
            password TEXT NOT NULL,
            session_id TEXT,
            perfil TEXT DEFAULT 'operador'
        );
        CREATE TABLE empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_fantasia TEXT NOT NULL,
            razao_social TEXT,
            cnpj TEXT,
            telefone TEXT,
            email TEXT,
            situacao_cadastral TEXT,
            data_situacao_cadastral TEXT
        );
        CREATE TABLE fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            telefone TEXT,
            email TEXT,
            situacao_cadastral TEXT,
            data_situacao_cadastral TEXT
        );
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade REAL DEFAULT 0,
            preco REAL NOT NULL,
            empresa_id INTEGER REFERENCES empresas(id),
            fornecedor_id INTEGER REFERENCES fornecedores(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER REFERENCES produtos(id),
            quantidade INTEGER,
            preco_unitario REAL,
            total REAL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed: admin com senha "testpass"
    c.execute(
        "INSERT INTO usuarios (username, password, perfil) VALUES (?, ?, ?)",
        ("admin", hash_password("testpass"), "admin"),
    )

    # Seed: empresa e fornecedor para testes de produto
    c.execute(
        "INSERT INTO empresas (nome_fantasia, razao_social, cnpj, telefone, email) VALUES (?, ?, ?, ?, ?)",
        ("Empresa Teste", "Empresa Teste LTDA", "00.000.000/0001-00", "11999999999", "teste@empresa.com"),
    )
    c.execute(
        "INSERT INTO fornecedores (nome, cnpj, telefone, email) VALUES (?, ?, ?, ?)",
        ("Fornecedor Teste", "11.111.111/0001-11", "11988888888", "forn@teste.com"),
    )

    # Seed: produto com estoque
    c.execute(
        "INSERT INTO produtos (nome, quantidade, preco, empresa_id, fornecedor_id) VALUES (?, ?, ?, ?, ?)",
        ("Produto Teste", 10, 25.00, 1, 1),
    )

    conn.commit()
    return conn


@pytest.fixture()
def override_db():
    """
    Substitui get_db() em todas as rotas por uma conexão em memória isolada.
    Cada teste recebe um banco limpo e independente.
    """
    test_conn = create_test_db()

    def get_test_db():
        try:
            yield test_conn
        finally:
            pass  # Não fecha aqui — o fixture fecha ao final

    app.dependency_overrides[get_db] = get_test_db
    yield test_conn
    app.dependency_overrides.clear()
    test_conn.close()


@pytest.fixture()
def client(override_db):
    """Cliente anônimo com banco em memória isolado."""
    return TestClient(app)


@pytest.fixture()
def authenticated_client(override_db):
    """Cliente com sessão de admin já autenticada."""
    session_id = "test-session-123"
    override_db.execute(
        "UPDATE usuarios SET session_id = ? WHERE username = 'admin'", (session_id,)
    )
    override_db.commit()
    return TestClient(app, cookies={"session_id": session_id})


# ---------------------------------------------------------------------------
# Testes de autenticação
# ---------------------------------------------------------------------------

def test_login_page_abre(client):
    """Página de login retorna 200 com o texto 'Login'."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text


def test_login_credenciais_invalidas(client):
    """Login com senha errada exibe mensagem de erro."""
    response = client.post("/login", data={"username": "admin", "password": "errada"})
    assert response.status_code == 200
    assert "Credenciais Inválidas" in response.text


def test_login_credenciais_validas(client):
    """Login com credenciais corretas redireciona para o dashboard."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_logout_remove_sessao(authenticated_client):
    """Logout redireciona para /login."""
    response = authenticated_client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


# ---------------------------------------------------------------------------
# Testes de proteção de rotas (sem autenticação)
# ---------------------------------------------------------------------------

def test_dashboard_sem_auth_redireciona(client):
    """Dashboard redireciona para login quando não autenticado."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303


def test_empresas_sem_auth_redireciona(client):
    """Rota /empresas redireciona quando não autenticado."""
    response = client.get("/empresas", follow_redirects=False)
    assert response.status_code == 303


def test_produtos_sem_auth_redireciona(client):
    """Rota /produtos redireciona quando não autenticado."""
    response = client.get("/produtos", follow_redirects=False)
    assert response.status_code == 303


def test_usuarios_sem_auth_redireciona(client):
    """Rota /usuarios redireciona quando não autenticado."""
    response = client.get("/usuarios", follow_redirects=False)
    assert response.status_code == 303


# ---------------------------------------------------------------------------
# Testes de CRUD — Produtos
# ---------------------------------------------------------------------------

def test_listar_produtos_autenticado(authenticated_client):
    """Página de produtos carrega com status 200."""
    response = authenticated_client.get("/produtos")
    assert response.status_code == 200
    assert "Produto Teste" in response.text


def test_criar_produto(authenticated_client):
    """Novo produto é inserido e redireciona para /produtos."""
    response = authenticated_client.post(
        "/produtos/novo",
        data={
            "nome": "Novo Produto",
            "quantidade": "5",
            "preco": "15.00",
            "empresa_id": "1",
            "fornecedor_id": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/produtos"


def test_deletar_produto(authenticated_client, override_db):
    """Produto é removido do banco após deleção."""
    response = authenticated_client.post("/produtos/deletar/1", follow_redirects=False)
    assert response.status_code == 303
    produto = override_db.execute("SELECT * FROM produtos WHERE id = 1").fetchone()
    assert produto is None


def test_editar_produto_rota_correta(authenticated_client, override_db):
    """POST /produtos/editar/{id} atualiza o produto e redireciona."""
    response = authenticated_client.post(
        "/produtos/editar/1",
        data={
            "nome": "Produto Editado",
            "quantidade": "99",
            "preco": "7.50",
            "empresa_id": "1",
            "fornecedor_id": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/produtos"
    produto = override_db.execute("SELECT nome, quantidade FROM produtos WHERE id = 1").fetchone()
    assert produto["nome"] == "Produto Editado"
    assert produto["quantidade"] == 99


def test_editar_produto_rota_antiga_nao_existe(authenticated_client):
    """A rota antiga POST /editar_produto/{id} não deve mais existir (404)."""
    response = authenticated_client.post(
        "/editar_produto/1",
        data={"nome": "X", "quantidade": "1", "preco": "1", "empresa_id": "1", "fornecedor_id": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 404  # rota removida — não existe mais


# ---------------------------------------------------------------------------
# Testes de CRUD — Vendas
# ---------------------------------------------------------------------------

def test_registrar_venda_reduz_estoque(authenticated_client, override_db):
    """Registrar uma venda diminui a quantidade do produto no estoque."""
    estoque_antes = override_db.execute(
        "SELECT quantidade FROM produtos WHERE id = 1"
    ).fetchone()["quantidade"]

    authenticated_client.post(
        "/vendas/nova",
        data={"produto_id": "1", "qtd_venda": "3"},
        follow_redirects=False,
    )

    estoque_depois = override_db.execute(
        "SELECT quantidade FROM produtos WHERE id = 1"
    ).fetchone()["quantidade"]

    assert estoque_depois == estoque_antes - 3


def test_venda_sem_estoque_suficiente_nao_processa(authenticated_client, override_db):
    """Venda maior que o estoque disponível não é registrada e exibe erro."""
    response = authenticated_client.post(
        "/vendas/nova",
        data={"produto_id": "1", "qtd_venda": "999"},
        follow_redirects=False,
    )
    estoque = override_db.execute(
        "SELECT quantidade FROM produtos WHERE id = 1"
    ).fetchone()["quantidade"]
    assert estoque == 10  # estoque não deve ter mudado
    # Deve renderizar a página com mensagem de erro (não redirecionar)
    assert response.status_code == 200
    assert "Estoque insuficiente" in response.text


def test_venda_quantidade_zero_rejeitada(authenticated_client, override_db):
    """Quantidade zero é rejeitada com mensagem de erro."""
    response = authenticated_client.post(
        "/vendas/nova",
        data={"produto_id": "1", "qtd_venda": "0"},
        follow_redirects=False,
    )
    estoque = override_db.execute(
        "SELECT quantidade FROM produtos WHERE id = 1"
    ).fetchone()["quantidade"]
    assert estoque == 10  # nenhuma alteração no estoque
    assert response.status_code == 200
    assert "maior que zero" in response.text


def test_venda_quantidade_negativa_rejeitada(authenticated_client, override_db):
    """Quantidade negativa é rejeitada com mensagem de erro."""
    response = authenticated_client.post(
        "/vendas/nova",
        data={"produto_id": "1", "qtd_venda": "-5"},
        follow_redirects=False,
    )
    estoque = override_db.execute(
        "SELECT quantidade FROM produtos WHERE id = 1"
    ).fetchone()["quantidade"]
    assert estoque == 10
    assert response.status_code == 200
    assert "maior que zero" in response.text


# ---------------------------------------------------------------------------
# Testes de API
# ---------------------------------------------------------------------------

def test_api_retorna_json(authenticated_client):
    """Endpoint /api/produtos/{id} retorna JSON com a chave 'estoque'."""
    response = authenticated_client.get("/api/produtos/1")
    assert response.status_code == 200
    data = response.json()
    assert "estoque" in data
    assert data["empresa_id"] == 1


def test_api_empresa_sem_produtos_retorna_lista_vazia(authenticated_client):
    """Endpoint retorna lista vazia para empresa sem produtos."""
    response = authenticated_client.get("/api/produtos/999")
    assert response.status_code == 200
    assert response.json()["estoque"] == []


# ---------------------------------------------------------------------------
# Testes de gestão de usuários (admin)
# ---------------------------------------------------------------------------

def test_criar_usuario_como_admin(authenticated_client, override_db):
    """Admin consegue criar novo usuário."""
    authenticated_client.post(
        "/usuarios/novo",
        data={"username": "novouser", "password": "senha123", "perfil": "operador"},
        follow_redirects=False,
    )
    user = override_db.execute(
        "SELECT * FROM usuarios WHERE username = 'novouser'"
    ).fetchone()
    assert user is not None
    assert user["perfil"] == "operador"


def test_usuario_nao_admin_nao_cria_usuario(override_db):
    """Usuário sem perfil admin não consegue criar usuário."""
    # Cria usuário operador e autentica
    override_db.execute(
        "INSERT INTO usuarios (username, password, perfil, session_id) VALUES (?, ?, ?, ?)",
        ("operador", hash_password("op123"), "operador", "op-session"),
    )
    override_db.commit()

    op_client = TestClient(app, cookies={"session_id": "op-session"})
    response = op_client.post(
        "/usuarios/novo",
        data={"username": "hacker", "password": "123", "perfil": "admin"},
        follow_redirects=False,
    )
    # Deve redirecionar sem criar
    assert response.status_code == 303
    user = override_db.execute(
        "SELECT * FROM usuarios WHERE username = 'hacker'"
    ).fetchone()
    assert user is None


# ---------------------------------------------------------------------------
# Testes dos bugs críticos corrigidos (#26, #27, #28, #29)
# ---------------------------------------------------------------------------

def test_logout_invalida_sessao_no_banco(authenticated_client, override_db):
    """Logout deve limpar session_id no banco, não apenas o cookie. (bug #26)"""
    # Confirma que há sessão ativa antes do logout
    usuario = override_db.execute(
        "SELECT session_id FROM usuarios WHERE username = 'admin'"
    ).fetchone()
    assert usuario["session_id"] is not None

    authenticated_client.get("/logout", follow_redirects=False)

    # Após logout, session_id deve ser NULL no banco
    usuario = override_db.execute(
        "SELECT session_id FROM usuarios WHERE username = 'admin'"
    ).fetchone()
    assert usuario["session_id"] is None


def test_pagina_cadastrar_produto_existe(authenticated_client):
    """GET /produtos/novo deve retornar 200 (template cadastrar_produto.html existe). (bug #27)"""
    response = authenticated_client.get("/produtos/novo")
    assert response.status_code == 200
    assert "Cadastrar Produto" in response.text


def test_editar_usuario_page_existe(authenticated_client, override_db):
    """GET /usuarios/editar/{id} deve retornar 200 com formulário preenchido. (bug #28)"""
    response = authenticated_client.get("/usuarios/editar/1")
    assert response.status_code == 200
    assert "admin" in response.text


def test_criar_fornecedor(authenticated_client, override_db):
    """POST /fornecedores/novo deve inserir fornecedor no banco. (bug #29)"""
    response = authenticated_client.post(
        "/fornecedores/novo",
        data={"nome": "Novo Fornecedor XYZ", "cnpj": "22.222.222/0001-22",
              "telefone": "(11) 99999-9999", "email": "xyz@fornecedor.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    fornecedor = override_db.execute(
        "SELECT * FROM fornecedores WHERE nome = 'Novo Fornecedor XYZ'"
    ).fetchone()
    assert fornecedor is not None
    assert fornecedor["cnpj"] == "22.222.222/0001-22"


def test_deletar_fornecedor(authenticated_client, override_db):
    """POST /fornecedores/deletar/{id} deve remover fornecedor do banco. (bug #29)"""
    response = authenticated_client.post("/fornecedores/deletar/1", follow_redirects=False)
    assert response.status_code == 303
    fornecedor = override_db.execute(
        "SELECT * FROM fornecedores WHERE id = 1"
    ).fetchone()
    assert fornecedor is None


# ---------------------------------------------------------------------------
# Testes de autenticação nas rotas que não tinham proteção
# ---------------------------------------------------------------------------

def test_criar_produto_sem_auth_redireciona(client):
    """POST /produtos/novo sem autenticação deve redirecionar para /login."""
    response = client.post(
        "/produtos/novo",
        data={"nome": "X", "quantidade": "1", "preco": "1.0",
              "empresa_id": "1", "fornecedor_id": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_criar_empresa_sem_auth_redireciona(client):
    """POST /empresas/nova sem autenticação deve redirecionar."""
    response = client.post(
        "/empresas/nova",
        data={"nome": "X", "razao_social": "X", "cnpj": "0",
              "tel": "0", "email": "x@x.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_editar_empresa_sem_auth_redireciona(client):
    """POST /empresas/editar/{id} sem autenticação deve redirecionar."""
    response = client.post(
        "/empresas/editar/1",
        data={"nome": "X", "cnpj": "0", "tel": "0", "email": "x@x.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_criar_empresa_usuario_nao_admin_bloqueado(override_db):
    """Usuário sem perfil admin não pode criar empresa."""
    override_db.execute(
        "INSERT INTO usuarios (username, password, perfil, session_id) VALUES (?, ?, ?, ?)",
        ("operador2", hash_password("op123"), "operador", "op2-session"),
    )
    override_db.commit()
    op_client = TestClient(app, cookies={"session_id": "op2-session"})
    response = op_client.post(
        "/empresas/nova",
        data={"nome": "Empresa X", "razao_social": "X", "cnpj": "0",
              "tel": "0", "email": "x@x.com"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    empresa = override_db.execute(
        "SELECT * FROM empresas WHERE nome_fantasia = 'Empresa X'"
    ).fetchone()
    assert empresa is None


# ---------------------------------------------------------------------------
# Testes de rotas com risco médio sem cobertura anterior
# ---------------------------------------------------------------------------

def test_deletar_empresa(authenticated_client, override_db):
    """POST /empresas/deletar/{id} remove a empresa do banco."""
    response = authenticated_client.post(
        "/empresas/deletar/1", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/empresas"
    empresa = override_db.execute(
        "SELECT * FROM empresas WHERE id = 1"
    ).fetchone()
    assert empresa is None


def test_deletar_empresa_sem_auth_redireciona(client):
    """POST /empresas/deletar/{id} sem autenticação redireciona."""
    response = client.post("/empresas/deletar/1", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"] or response.headers["location"] == "/"


def test_deletar_empresa_usuario_nao_admin_bloqueado(override_db):
    """Usuário sem perfil admin não pode deletar empresa."""
    override_db.execute(
        "INSERT INTO usuarios (username, password, perfil, session_id) VALUES (?, ?, ?, ?)",
        ("operador3", hash_password("op123"), "operador", "op3-session"),
    )
    override_db.commit()
    op_client = TestClient(app, cookies={"session_id": "op3-session"})
    op_client.post("/empresas/deletar/1", follow_redirects=False)
    empresa = override_db.execute(
        "SELECT * FROM empresas WHERE id = 1"
    ).fetchone()
    assert empresa is not None  # não deve ter sido deletada


def test_editar_fornecedor(authenticated_client, override_db):
    """POST /fornecedores/editar/{id} atualiza os dados do fornecedor."""
    response = authenticated_client.post(
        "/fornecedores/editar/1",
        data={
            "nome": "Fornecedor Atualizado",
            "cnpj": "99.999.999/0001-99",
            "telefone": "(11) 11111-1111",
            "email": "novo@fornecedor.com",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/fornecedores"
    fornecedor = override_db.execute(
        "SELECT * FROM fornecedores WHERE id = 1"
    ).fetchone()
    assert fornecedor["nome"] == "Fornecedor Atualizado"
    assert fornecedor["cnpj"] == "99.999.999/0001-99"


def test_editar_fornecedor_sem_auth_redireciona(client):
    """POST /fornecedores/editar/{id} sem autenticação redireciona para /login."""
    response = client.post(
        "/fornecedores/editar/1",
        data={"nome": "X", "cnpj": None, "telefone": None, "email": None},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


# ---------------------------------------------------------------------------
# Testes do PR #15 — deleção via POST (proteção CSRF)
# ---------------------------------------------------------------------------

def test_deletar_produto_via_get_nao_existe(authenticated_client):
    """GET /produtos/deletar/{id} não deve existir — deleção só via POST. (PR #15)"""
    response = authenticated_client.get("/produtos/deletar/1", follow_redirects=False)
    assert response.status_code == 405  # Method Not Allowed


def test_deletar_fornecedor_via_get_nao_existe(authenticated_client):
    """GET /fornecedores/deletar/{id} não deve existir — deleção só via POST. (PR #15)"""
    response = authenticated_client.get("/fornecedores/deletar/1", follow_redirects=False)
    assert response.status_code == 405


def test_deletar_empresa_via_get_nao_existe(authenticated_client):
    """GET /empresas/deletar/{id} não deve existir — deleção só via POST. (PR #15)"""
    response = authenticated_client.get("/empresas/deletar/1", follow_redirects=False)
    assert response.status_code == 405


def test_deletar_usuario_via_get_nao_existe(authenticated_client):
    """GET /usuarios/deletar/{id} não deve existir — deleção só via POST. (PR #15)"""
    response = authenticated_client.get("/usuarios/deletar/1", follow_redirects=False)
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# Testes do PR #17 — flags de segurança no cookie de sessão
# ---------------------------------------------------------------------------

def test_cookie_sessao_tem_flag_httponly(client):
    """Cookie session_id deve ter flag HttpOnly para impedir acesso via JS. (PR #17)"""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    cookie_header = response.headers.get("set-cookie", "")
    assert "session_id" in cookie_header
    assert "httponly" in cookie_header.lower()


def test_cookie_sessao_tem_flag_samesite(client):
    """Cookie session_id deve ter SameSite=lax para proteção CSRF. (PR #17)"""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    cookie_header = response.headers.get("set-cookie", "")
    assert "samesite" in cookie_header.lower()


def test_logout_apaga_cookie_sessao(authenticated_client):
    """Logout deve enviar Set-Cookie apagando session_id (Max-Age=0). (PR #17)"""
    response = authenticated_client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    cookie_header = response.headers.get("set-cookie", "")
    # O cookie deve ser apagado (Max-Age=0 ou expires no passado)
    assert "session_id" in cookie_header
    assert "max-age=0" in cookie_header.lower() or "expires" in cookie_header.lower()


# ---------------------------------------------------------------------------
# Testes do PR #18 — hashing bcrypt de senhas
# ---------------------------------------------------------------------------

def test_hash_password_nao_armazena_texto_plano():
    """O hash gerado por hash_password não deve ser igual à senha original. (PR #18)"""
    from main import hash_password
    senha = "minha_senha_secreta"
    hashed = hash_password(senha)
    assert hashed != senha


def test_hash_password_usa_bcrypt():
    """O hash gerado deve começar com prefixo bcrypt '$2b$'. (PR #18)"""
    from main import hash_password
    hashed = hash_password("qualquer_senha")
    assert hashed.startswith("$2b$")


def test_verify_password_correto():
    """verify_password retorna True para senha correta. (PR #18)"""
    from main import hash_password, verify_password
    senha = "senha_correta"
    hashed = hash_password(senha)
    assert verify_password(senha, hashed) is True


def test_verify_password_incorreto():
    """verify_password retorna False para senha errada. (PR #18)"""
    from main import hash_password, verify_password
    hashed = hash_password("senha_correta")
    assert verify_password("senha_errada", hashed) is False


def test_dois_hashes_da_mesma_senha_sao_diferentes():
    """bcrypt gera salt aleatório — dois hashes da mesma senha devem diferir. (PR #18)"""
    from main import hash_password
    h1 = hash_password("mesma_senha")
    h2 = hash_password("mesma_senha")
    assert h1 != h2
