from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import uuid
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURAÇÕES ---
# Banco de dados: por padrão usa SQLite local. Em produção pode ser trocado
# para qualquer caminho ou URL compatível com sqlite3, apenas definindo
# DATABASE_URL no .env ou nas variáveis de ambiente da plataforma.
DATABASE_URL = os.environ.get("DATABASE_URL", "estoque.db")

# Em produção (ENVIRONMENT=production), o cookie só é enviado em HTTPS.
SECURE_COOKIE = os.environ.get("ENVIRONMENT", "development") == "production"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- BANCO DE DADOS ---
def get_db():
    """
    Dependência injetável via Depends(get_db).
    Garante que a conexão é sempre fechada ao final da requisição,
    mesmo que ocorra uma exceção durante o processamento.
    """
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password: str) -> str:
    """Gera hash bcrypt com salt automático. Retorna string UTF-8."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha contra hash bcrypt armazenado."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# Auxiliar para verificar login em todas as rotas
def get_current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    user = conn.execute("SELECT * FROM usuarios WHERE session_id = ?", (session_id,)).fetchone()
    return user

# --- ROTAS DE AUTENTICAÇÃO ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()

    if user and verify_password(password, user['password']):
        session_id = str(uuid.uuid4())
        conn.execute("UPDATE usuarios SET session_id = ? WHERE id = ?", (session_id, user['id']))
        conn.commit()

        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,       # impede acesso via JavaScript
            samesite="lax",      # proteção contra CSRF
            secure=SECURE_COOKIE # True em produção (HTTPS), False em dev
        )
        return response

    return templates.TemplateResponse(request, "login.html", {"error": "Credenciais Inválidas"})

@app.get("/logout")
async def logout(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id:
        conn.execute("UPDATE usuarios SET session_id = NULL WHERE session_id = ?", (session_id,))
        conn.commit()
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_id")
    return response

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)

    total_produtos = conn.execute("SELECT SUM(quantidade) FROM produtos").fetchone()[0] or 0
    total_vendas = conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
    total_empresas = conn.execute("SELECT COUNT(*) FROM empresas").fetchone()[0]
    total_fornecedores = conn.execute("SELECT COUNT(*) FROM fornecedores").fetchone()[0]

    dados_grafico = conn.execute("""
        SELECT e.nome_fantasia, SUM(p.quantidade) as total 
        FROM produtos p 
        JOIN empresas e ON p.empresa_id = e.id 
        GROUP BY e.id
    """).fetchall()

    dados_fornecedores = conn.execute("""
        SELECT f.nome, COUNT(p.id)
        FROM produtos p
        JOIN fornecedores f ON p.fornecedor_id = f.id
        GROUP BY f.nome
    """).fetchall()

    labels = [d['nome_fantasia'] for d in dados_grafico]
    valores = [d['total'] for d in dados_grafico]

    vendas_recentes = conn.execute("""
        SELECT v.*, p.nome FROM vendas v 
        JOIN produtos p ON v.produto_id = p.id 
        ORDER BY v.id DESC LIMIT 5
    """).fetchall()

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "total_produtos": total_produtos,
        "total_vendas": total_vendas,
        "total_empresas": total_empresas,
        "total_fornecedores": total_fornecedores,
        "labels": labels,
        "valores": valores,
        "vendas_recentes": vendas_recentes
    })

# --- PRODUTOS ---
@app.get("/produtos", response_class=HTMLResponse)
async def listar_produtos(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)

    produtos = conn.execute("""
        SELECT p.*, e.nome_fantasia AS empresa_nome, f.nome AS fornecedor_nome
        FROM produtos p
        LEFT JOIN empresas e ON p.empresa_id = e.id
        LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
    """).fetchall()

    empresas = conn.execute("SELECT id, nome_fantasia FROM empresas").fetchall()
    fornecedores = conn.execute("SELECT id, nome FROM fornecedores").fetchall()

    return templates.TemplateResponse(request, "produtos.html", {
        "user": user,
        "produtos": produtos,
        "empresas": empresas,
        "fornecedores": fornecedores
    })

# NOVO PRODUTO
@app.post("/produtos/novo")
async def novo_produto(
    request: Request,
    nome: str = Form(...),
    quantidade: float = Form(...),
    preco: float = Form(...),
    empresa_id: int = Form(...),
    fornecedor_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    conn.execute("""
        INSERT INTO produtos (nome, quantidade, preco, empresa_id, fornecedor_id) 
        VALUES (?, ?, ?, ?, ?)
    """, (nome, quantidade, preco, empresa_id, fornecedor_id))
    conn.commit()
    return RedirectResponse(url="/produtos", status_code=303)

@app.get("/produtos/novo")
async def exibir_formulario_cadastro(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    empresas = conn.execute("SELECT id, nome_fantasia FROM empresas").fetchall()
    fornecedores = conn.execute("SELECT id, nome FROM fornecedores").fetchall()
    return templates.TemplateResponse(request, "cadastrar_produto.html", {
        "user": user,
        "empresas": empresas,
        "fornecedores": fornecedores
    })

# EDITAR PRODUTO
@app.get("/produtos/editar/{id}", response_class=HTMLResponse)
async def editar_produto_page(request: Request, id: int, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)

    produto = conn.execute("SELECT * FROM produtos WHERE id = ?", (id,)).fetchone()
    empresas = conn.execute("SELECT id, nome_fantasia FROM empresas").fetchall()
    fornecedores = conn.execute("SELECT id, nome FROM fornecedores").fetchall()

    return templates.TemplateResponse(request, "editar_produto.html", {
        "user": user, "produto": produto,
        "empresas": empresas, "fornecedores": fornecedores
    })

@app.post("/produtos/editar/{id}")
async def atualizar_produto(
    request: Request,
    id: int,
    nome: str = Form(...),
    quantidade: float = Form(...),
    preco: float = Form(...),
    empresa_id: int = Form(...),
    fornecedor_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    conn.execute("""
        UPDATE produtos 
        SET nome = ?, quantidade = ?, preco = ?, empresa_id = ?, fornecedor_id = ? 
        WHERE id = ?
    """, (nome, quantidade, preco, empresa_id, fornecedor_id, id))
    conn.commit()
    return RedirectResponse(url="/produtos", status_code=303)

# DELETAR PRODUTO
@app.post("/produtos/deletar/{id}")
async def deletar_produto(request: Request, id: int, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)
    conn.execute("DELETE FROM produtos WHERE id = ?", (id,))
    conn.commit()
    return RedirectResponse(url="/produtos", status_code=303)

# --- GESTÃO DE USUÁRIOS ---
@app.get("/usuarios", response_class=HTMLResponse)
async def listar_usuarios(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)

    cursor = conn.execute("SELECT id, username, perfil FROM usuarios")
    lista_limpa = [dict(row) for row in cursor.fetchall()]

    return templates.TemplateResponse(request, "usuarios.html", {
        "user": dict(user),
        "usuarios": lista_limpa
    })

@app.post("/usuarios/novo")
async def novo_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    perfil: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)

    try:
        conn.execute(
            "INSERT INTO usuarios (username, password, perfil) VALUES (?, ?, ?)",
            (username, hash_password(password), perfil)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # usuário já existe

    return RedirectResponse(url="/usuarios", status_code=303)

@app.post("/usuarios/deletar/{id}")
async def deletar_usuario(request: Request, id: int, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if user and user['perfil'] == 'admin' and user['id'] != id:
        conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
        conn.commit()
    return RedirectResponse(url="/usuarios", status_code=303)

@app.get("/usuarios/editar/{user_id}", response_class=HTMLResponse)
async def editar_usuario_page(request: Request, user_id: int, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)
    usuario = conn.execute("SELECT id, username, perfil FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    if not usuario:
        return RedirectResponse(url="/usuarios", status_code=303)
    return templates.TemplateResponse(request, "editar_usuario.html", {
        "user": user, "usuario": dict(usuario)
    })

@app.post("/usuarios/editar/{user_id}")
async def editar_usuario(
    user_id: int,
    request: Request,
    username: str = Form(...),
    perfil: str = Form(...),
    password: str = Form(None),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)

    if password:
        conn.execute(
            "UPDATE usuarios SET username = ?, perfil = ?, password = ? WHERE id = ?",
            (username, perfil, hash_password(password), user_id)
        )
    else:
        conn.execute(
            "UPDATE usuarios SET username = ?, perfil = ? WHERE id = ?",
            (username, perfil, user_id)
        )
    conn.commit()
    return RedirectResponse(url="/usuarios", status_code=303)

# --- FORNECEDORES ---
@app.get("/fornecedores", response_class=HTMLResponse)
async def listar_fornecedores(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)

    fornecedores = conn.execute("SELECT * FROM fornecedores").fetchall()
    return templates.TemplateResponse(request, "fornecedores.html", {
        "user": user, "fornecedores": fornecedores
    })

@app.post("/fornecedores/novo")
async def novo_fornecedor(
    request: Request,
    nome: str = Form(...),
    cnpj: str = Form(None),
    telefone: str = Form(None),
    email: str = Form(None),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    conn.execute(
        "INSERT INTO fornecedores (nome, cnpj, telefone, email) VALUES (?, ?, ?, ?)",
        (nome, cnpj, telefone, email)
    )
    conn.commit()
    return RedirectResponse(url="/fornecedores", status_code=303)

@app.post("/fornecedores/deletar/{id}")
async def deletar_fornecedor(
    request: Request,
    id: int,
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    conn.execute("DELETE FROM fornecedores WHERE id = ?", (id,))
    conn.commit()
    return RedirectResponse(url="/fornecedores", status_code=303)

@app.post("/fornecedores/editar/{id}")
async def editar_fornecedor(
    request: Request,
    id: int,
    nome: str = Form(...),
    cnpj: str = Form(None),
    telefone: str = Form(None),
    email: str = Form(None),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    conn.execute("""
        UPDATE fornecedores 
        SET nome = ?, cnpj = ?, telefone = ?, email = ? 
        WHERE id = ?
    """, (nome, cnpj, telefone, email, id))
    conn.commit()
    return RedirectResponse(url="/fornecedores", status_code=303)

# --- VENDAS ---
@app.get("/vendas", response_class=HTMLResponse)
async def pagina_vendas(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user: return RedirectResponse(url="/login", status_code=303)

    produtos = conn.execute("SELECT * FROM produtos WHERE quantidade > 0").fetchall()
    vendas = conn.execute("""
        SELECT v.*, p.nome 
        FROM vendas v 
        JOIN produtos p ON v.produto_id = p.id 
        ORDER BY v.data DESC
    """).fetchall()

    return templates.TemplateResponse(request, "vendas.html", {
        "user": user,
        "produtos": produtos,
        "vendas": vendas
    })

@app.post("/vendas/nova")
async def registrar_venda(
    request: Request,
    produto_id: int = Form(...),
    qtd_venda: int = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    erro = None

    if qtd_venda <= 0:
        erro = "A quantidade deve ser maior que zero."
    else:
        prod = conn.execute("SELECT quantidade, preco FROM produtos WHERE id = ?", (produto_id,)).fetchone()

        if not prod:
            erro = "Produto não encontrado."
        elif qtd_venda > prod['quantidade']:
            erro = f"Estoque insuficiente. Disponível: {prod['quantidade']} unidade(s)."
        else:
            total = qtd_venda * prod['preco']
            conn.execute(
                "INSERT INTO vendas (produto_id, quantidade, preco_unitario, total) VALUES (?, ?, ?, ?)",
                (produto_id, qtd_venda, prod['preco'], total)
            )
            conn.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (qtd_venda, produto_id))
            conn.commit()

    if erro:
        produtos = conn.execute("SELECT * FROM produtos WHERE quantidade > 0").fetchall()
        vendas = conn.execute("""
            SELECT v.*, p.nome
            FROM vendas v
            JOIN produtos p ON v.produto_id = p.id
            ORDER BY v.data DESC
        """).fetchall()
        return templates.TemplateResponse(request, "vendas.html", {
            "user": user,
            "produtos": produtos,
            "vendas": vendas,
            "erro_venda": erro,
            "produto_id_selecionado": produto_id,
            "qtd_venda": qtd_venda,
        })

    return RedirectResponse(url="/vendas", status_code=303)

# --- EMPRESAS ---
@app.get("/empresas", response_class=HTMLResponse)
async def listar_empresas(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)

    empresas = conn.execute("SELECT * FROM empresas ORDER BY nome_fantasia").fetchall()
    return templates.TemplateResponse(request, "empresas.html", {
        "user": user, "empresas": empresas
    })

@app.post("/empresas/nova")
async def nova_empresa(
    request: Request,
    nome: str = Form(...),
    razao_social: str = Form(...),
    cnpj: str = Form(...),
    tel: str = Form(...),
    email: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)
    conn.execute("""
        INSERT INTO empresas (nome_fantasia, razao_social, cnpj, telefone, email) 
        VALUES (?, ?, ?, ?, ?)
    """, (nome, razao_social, cnpj, tel, email))
    conn.commit()
    return RedirectResponse(url="/empresas", status_code=303)

@app.post("/empresas/deletar/{id}")
async def deletar_empresa(request: Request, id: int, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin': return RedirectResponse(url="/", status_code=303)
    conn.execute("DELETE FROM empresas WHERE id = ?", (id,))
    conn.commit()
    return RedirectResponse(url="/empresas", status_code=303)

@app.get("/empresas/editar/{id}", response_class=HTMLResponse)
async def editar_empresa_page(request: Request, id: int, conn: sqlite3.Connection = Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)

    empresa = conn.execute("SELECT * FROM empresas WHERE id = ?", (id,)).fetchone()
    if not empresa:
        return RedirectResponse(url="/empresas", status_code=303)

    return templates.TemplateResponse(request, "editar_empresa.html", {
        "user": user, "empresa": empresa
    })

@app.post("/empresas/editar/{id}")
async def atualizar_empresa(
    request: Request,
    id: int,
    nome: str = Form(...),
    cnpj: str = Form(...),
    tel: str = Form(...),
    email: str = Form(...),
    conn: sqlite3.Connection = Depends(get_db)
):
    user = get_current_user(request, conn)
    if not user or user['perfil'] != 'admin':
        return RedirectResponse(url="/", status_code=303)
    conn.execute("""
        UPDATE empresas 
        SET nome_fantasia = ?, cnpj = ?, telefone = ?, email = ? 
        WHERE id = ?
    """, (nome, cnpj, tel, email, id))
    conn.commit()
    return RedirectResponse(url="/empresas", status_code=303)

# --- API ---
@app.get("/api/produtos/{empresa_id}")
async def api_listar_produtos(empresa_id: int, conn: sqlite3.Connection = Depends(get_db)):
    produtos = conn.execute(
        "SELECT nome, quantidade, preco FROM produtos WHERE empresa_id = ?", (empresa_id,)
    ).fetchall()
    return {"empresa_id": empresa_id, "estoque": [dict(p) for p in produtos]}
