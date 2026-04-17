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
            password TEXT NOT NULL,
            session_id TEXT,
            perfil TEXT DEFAULT 'user'
        );
        CREATE TABLE empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_fantasia TEXT NOT NULL,
            razao_social TEXT,
            cnpj TEXT,
            telefone TEXT,
            email TEXT
        );
        CREATE TABLE fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            telefone TEXT,
            email TEXT
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
