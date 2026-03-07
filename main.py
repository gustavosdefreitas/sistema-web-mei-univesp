from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
import hashlib

app = FastAPI()

def get_db():
    conn = sqlite3.connect('estoque.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_authenticated(request: Request):
    session = request.cookies.get("session_id", "")
    if not session: return False
    conn = get_db()
    user = conn.execute("SELECT id FROM usuarios WHERE session_id = ?", (session,)).fetchone()
    conn.close()
    return user is not None

# LOGIN
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html><head><title>🔐 Login</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="bg-light">
<div class="container py-5">
<div class="row justify-content-center">
<div class="col-md-4">
<div class="card shadow-lg">
<div class="card-header bg-primary text-white text-center">
<h3>🔐 Estoque MEI</h3>
</div>
<div class="card-body p-4">
<form method="POST" action="/login/">
<div class="mb-3">
<input type="text" name="username" class="form-control form-control-lg" placeholder="admin" required>
</div>
<div class="mb-3">
<input type="password" name="password" class="form-control form-control-lg" placeholder="123456" required>
</div>
<button class="btn btn-primary w-100 btn-lg">Entrar</button>
</form>
</div>
</div>
</div></div></div></body></html>
    """)

@app.post("/login/")
async def login(username: str = Form(...), password: str = Form(...)):
    conn = get_db()
    hashed = hash_password(password)
    user = conn.execute("SELECT id FROM usuarios WHERE username = ? AND password = ?", 
                       (username, hashed)).fetchone()
    conn.close()
    
    if user:
        session_id = hashlib.sha256(f"{username}{hashed}".encode()).hexdigest()
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        
        conn = get_db()
        conn.execute("UPDATE usuarios SET session_id = ? WHERE id = ?", (session_id, user['id']))
        conn.commit()
        conn.close()
        return response
    
    raise HTTPException(status_code=400, detail="Credenciais inválidas!")

#SAIR DO SISTEMA
@app.get("/logout/")
async def logout(request: Request):
    session_id = request.cookies.get("session_id", "")
    if session_id:
        conn = get_db()
        conn.execute("UPDATE usuarios SET session_id = '' WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_id")
    return response

# DASHBOARD
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    produtos = conn.execute("SELECT * FROM produtos ORDER BY quantidade").fetchall()
    vendas = conn.execute("SELECT COALESCE(SUM(total), 0) as total FROM vendas").fetchone()
    total_vendas = vendas['total'] if vendas else 0
    conn.close()
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head><title>📊 Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand fw-bold" href="/"><i class="fas fa-boxes me-2"></i>Estoque MEI</a>
<div class="d-flex gap-2">
<a href="/vendas/nova" class="btn btn-success btn-sm">🛒 Nova Venda</a>
<a href="/usuarios" class="btn btn-warning btn-sm">👥 Usuários</a>
<a href="/produtos" class="btn btn-primary btn-sm">📦 Produtos</a>
<a href="/empresas" class="btn btn-success btn-sm">🏢 Empresas</a>
<a href="/minha-conta" class="btn btn-info btn-sm">⚙️ Minha Conta</a>
<a href="/logout/" class="btn btn-outline-light btn-sm">🚪 Sair</a>
</div>
</div>
</nav>
<div class="container py-4">
<h1 class="mb-4"><i class="fas fa-tachometer-alt me-2 text-primary"></i>Dashboard</h1>
<div class="row g-4 mb-4">
<div class="col-md-3">
<div class="card text-white bg-primary h-100">
<div class="card-body text-center">
<i class="fas fa-boxes fa-3x mb-3"></i>
<h2 class="display-4">{len(produtos)}</h2>
<p class="fs-5">Produtos</p>
</div></div></div>
<div class="col-md-3">
<div class="card text-white bg-success h-100">
<div class="card-body text-center">
<i class="fas fa-dollar-sign fa-3x mb-3"></i>
<h2 class="display-4">R$ {total_vendas:.2f}</h2>
<p class="fs-5">Vendas</p>
</div></div></div>
</div>
<div class="card shadow mb-4">
<div class="card-body">
<a href="/vendas/nova" class="btn btn-success btn-lg px-4">
<i class="fas fa-shopping-cart me-2"></i>Nova Venda
</a>
</div>
</div>
<div class="card shadow">
<div class="card-header"><h5>📦 Produtos</h5></div>
<div class="card-body">
<div class="table-responsive">
<table class="table table-hover">
<thead class="table-dark"><tr><th>Produto</th><th class="text-center">Estoque</th><th class="text-end">Preço</th></tr></thead>
<tbody>
""" + "".join([f"""
<tr><td><strong>{p['nome']}</strong></td>
<td class="text-center"><span class="badge {'bg-success' if p['quantidade']>5 else 'bg-warning'}">{p['quantidade']}</span></td>
<td class="text-end"><strong>R$ {p['preco']:.2f}</strong></td></tr>
""" for p in produtos]) + """
</tbody></table></div></div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

#usuarios (apenas admin)
@app.get("/usuarios", response_class=HTMLResponse)
async def usuarios(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    session_user = conn.execute("SELECT perfil FROM usuarios WHERE session_id = ?", 
                               (request.cookies.get("session_id", ""),)).fetchone()
    
    if not session_user or session_user['perfil'] != 'admin':
        conn.close()
        return HTMLResponse(content="<div class='alert alert-danger'>❌ Apenas admin!</div><a href='/'>Voltar</a>", status_code=403)
    
    usuarios = conn.execute("SELECT id, username, perfil FROM usuarios").fetchall()
    conn.close()
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head><title>👥 Usuários</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container"><a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/" class="btn btn-outline-light me-2">Dashboard</a><a href="/logout/" class="btn btn-outline-light">Sair</a></div>
</nav>
<div class="container py-4">
<h1><i class="fas fa-users me-2 text-primary"></i>Gerenciar Usuários</h1>
<div class="card shadow mb-4">
<div class="card-header bg-success text-white"><h5>Novo Usuário</h5></div>
<div class="card-body">
<form method="POST" action="/usuarios/novo">
<div class="row">
<div class="col-md-4 mb-3"><input name="username" class="form-control" placeholder="Usuário" required></div>
<div class="col-md-4 mb-3"><input name="password" type="password" class="form-control" placeholder="Senha" required></div>
<div class="col-md-4 mb-3">
<select name="perfil" class="form-select">
<option value="user">Usuário</option><option value="admin">Admin</option>
</select>
</div>
<button class="btn btn-success">Criar</button>
</div></form>
</div></div>
<div class="card shadow">
<div class="card-header bg-primary text-white"><h5>Usuários ({len(usuarios)})</h5></div>
<div class="card-body">
<table class="table">
<thead class="table-dark">
<tr><th>ID</th><th>Usuário</th><th>Perfil</th><th>Ações</th></tr>
</thead>
<tbody>
""" + "".join([f"""
<tr>
<td>#{u['id']}</td>
<td>{u['username']}</td>
<td><span class="badge {'bg-danger' if u['perfil']=='admin' else 'bg-success'}">{u['perfil'].upper()}</span></td>
<td>
<a href="/usuarios/editar/{u['id']}" class="btn btn-sm btn-primary me-1"><i class="fas fa-edit"></i></a>
<form method="POST" action="/usuarios/delete/{u['id']}" style="display:inline" onsubmit="return confirm('Excluir?')">
<button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
</form>
</td>
</tr>
""" for u in usuarios]) + """
</tbody></table></div></div></div></body></html>
    """)

#EDITAR USUÁRIO
@app.get("/usuarios/editar/{user_id}", response_class=HTMLResponse)
async def editar_usuario(request: Request, user_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    session_user = conn.execute("SELECT perfil FROM usuarios WHERE session_id = ?", 
                               (request.cookies.get("session_id", ""),)).fetchone()
    
    if not session_user or session_user['perfil'] != 'admin':
        conn.close()
        return HTMLResponse(content="<div class='alert alert-danger'>❌ Apenas admin!</div>", status_code=403)
    
    usuario = conn.execute("SELECT id, username, perfil FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    
    if not usuario:
        return HTMLResponse(content="<h1>❌ Usuário não encontrado!</h1><a href='/usuarios'>Voltar</a>", status_code=404)
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head><title>✏️ Editar Usuário</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/usuarios" class="btn btn-outline-light me-2">← Voltar Usuários</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-5">
<div class="row justify-content-center">
<div class="col-md-6">
<div class="card shadow-lg">
<div class="card-header bg-warning text-dark">
<h4><i class="fas fa-user-edit me-2"></i>Editar Usuário</h4>
</div>
<div class="card-body">
<form method="POST" action="/usuarios/atualizar/{usuario['id']}">
<div class="mb-3">
<label class="form-label fw-bold">👤 Nome de Usuário</label>
<input type="text" name="username" class="form-control form-control-lg" value="{usuario['username']}" required>
</div>
<div class="mb-3">
<label class="form-label fw-bold">🔐 Nova Senha (deixe vazio para manter)</label>
<input type="password" name="password" class="form-control form-control-lg" placeholder="Nova senha">
</div>
<div class="mb-3">
<label class="form-label fw-bold">🎭 Perfil</label>
<select name="perfil" class="form-select form-select-lg">
<option value="user" {'selected' if usuario['perfil']=='user' else ''}>Usuário Comum</option>
<option value="admin" {'selected' if usuario['perfil']=='admin' else ''}>Administrador</option>
</select>
</div>
<div class="d-grid gap-2 d-md-flex justify-content-end">
<a href="/usuarios" class="btn btn-secondary">Cancelar</a>
<button type="submit" class="btn btn-warning btn-lg px-4">
<i class="fas fa-save me-2"></i>Atualizar Usuário
</button>
</div>
</form>
</div>
</div>
</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

#ATUALIZAR USUÁRIO
@app.post("/usuarios/atualizar/{user_id}")
async def atualizar_usuario(request: Request, user_id: int, username: str = Form(...), 
                          password: str = Form(None), perfil: str = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    session_user = conn.execute("SELECT id, perfil FROM usuarios WHERE session_id = ?", 
                               (request.cookies.get("session_id", ""),)).fetchone()
    
    if not session_user or session_user['perfil'] != 'admin':
        conn.close()
        raise HTTPException(status_code=403)
    
    # Não permite alterar usuário logado
    #if session_user['id'] == user_id:
    #   conn.close()
    #   raise HTTPException(status_code=400, detail="Não pode alterar a si mesmo!")
    
    # Verifica usuário duplicado
    if username != conn.execute("SELECT username FROM usuarios WHERE id = ?", (user_id,)).fetchone()['username']:
        if conn.execute("SELECT id FROM usuarios WHERE username = ?", (username,)).fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Nome de usuário já existe!")
    
    # Atualiza dados
    if password:  # Nova senha
        hashed = hash_password(password)
        conn.execute("UPDATE usuarios SET username = ?, password = ?, perfil = ? WHERE id = ?", 
                    (username, hashed, perfil, user_id))
    else:  # Mantém senha atual
        conn.execute("UPDATE usuarios SET username = ?, perfil = ? WHERE id = ?", 
                    (username, perfil, user_id))
    
    conn.commit()
    conn.close()
    return RedirectResponse(url="/usuarios", status_code=303)

#NOVO USUÁRIO
@app.post("/usuarios/novo")
async def criar_usuario(request: Request, username: str = Form(...), password: str = Form(...), perfil: str = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    session_user = conn.execute("SELECT perfil FROM usuarios WHERE session_id = ?", 
                               (request.cookies.get("session_id", ""),)).fetchone()
    
    if not session_user or session_user['perfil'] != 'admin':
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas administradores!")
    
    # Verifica usuário duplicado
    if conn.execute("SELECT id FROM usuarios WHERE username = ?", (username,)).fetchone():
        raise HTTPException(status_code=400, detail="Usuário existe!")
    
    hashed = hash_password(password)
    conn.execute("INSERT INTO usuarios (username, password, perfil) VALUES (?, ?, ?)", 
                (username, hashed, perfil))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/usuarios", status_code=303)

@app.post("/usuarios/delete/{user_id}")
async def deletar_usuario(request: Request, userid: int):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    session_user = conn.execute("SELECT id FROM usuarios WHERE session_id = ?", 
                               (request.cookies.get("session_id", ""),)).fetchone()
    
    if not session_user or session_user['perfil'] != 'admin':
        conn.close()
        raise HTTPException(status_code=403, detail="Apenas administradores!")

    if session_user['id'] == user_id:
        raise HTTPException(status_code=400, detail="Não pode se deletar!")
    
    conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/usuarios", status_code=303)

# Vendas (simplificado)
@app.get("/vendas/nova")
async def nova_venda(request: Request):
    if not is_authenticated(request): return RedirectResponse(url="/login", status_code=303)
    conn = get_db()
    produtos = conn.execute("SELECT * FROM produtos WHERE quantidade > 0").fetchall()
    conn.close()
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head><title>Nova Venda</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light"><div class="container py-5">
<div class="row justify-content-center"><div class="col-md-6">
<div class="card shadow"><div class="card-header bg-success text-white"><h4>Nova Venda</h4></div>
<div class="card-body">
<form method="POST" action="/vendas/">
<select name="produto_id" class="form-select mb-3">
""" + "".join([f'<option value="{p["id"]}">{p["nome"]} (Est: {p["quantidade"]})</option>' for p in produtos]) + """
</select>
<input type="number" name="quantidade" class="form-control mb-3" min="1" required>
<button class="btn btn-success w-100">Vender</button>
</form><a href="/" class="btn btn-secondary w-100 mt-2">Cancelar</a>
</div></div></div></div></div></body></html>
    """)

@app.post("/vendas/")
async def vender(produto_id: int = Form(...), quantidade: int = Form(...)):
    conn = get_db()
    produto = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if produto['quantidade'] < quantidade:
        return HTMLResponse(content="❌ Estoque insuficiente!", status_code=400)
    
    total = quantidade * produto['preco']
    conn.execute("INSERT INTO vendas (produto_id, quantidade, preco_unitario, total) VALUES (?, ?, ?, ?)",
                (produto_id, quantidade, produto['preco'], total))
    conn.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (quantidade, produto_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

#MINHA CONTA
@app.get("/minha-conta", response_class=HTMLResponse)
async def minha_conta(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    session_id = request.cookies.get("session_id", "")
    conn = get_db()
    usuario = conn.execute("""
        SELECT id, username, perfil FROM usuarios 
        WHERE session_id = ? 
    """, (session_id,)).fetchone()
    conn.close()
    
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head>
<title>🔐 Minha Conta</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/" class="btn btn-outline-light me-2">← Dashboard</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-5">
<div class="row justify-content-center">
<div class="col-md-6">
<div class="card shadow-lg">
<div class="card-header bg-info text-white text-center">
<h3><i class="fas fa-user-cog me-2"></i>Minha Conta</h3>
<p class="mb-0">Alterar minha senha</p>
</div>
<div class="card-body">
<!-- INFO DO USUÁRIO -->
<div class="alert alert-success mb-4">
<i class="fas fa-user-check me-2"></i>
<strong>Usuário:</strong> {usuario['username']}<br>
<strong>Perfil:</strong> 
<span class="badge {'bg-danger' if usuario['perfil']=='admin' else 'bg-success'}">{usuario['perfil'].upper()}</span>
</div>

<form method="POST" action="/minha-conta/atualizar">
<div class="mb-4">
<label class="form-label fw-bold fs-5">🔐 Nova Senha</label>
<input type="password" name="nova_senha" class="form-control form-control-lg" placeholder="Digite nova senha" required>
</div>
<div class="mb-4">
<label class="form-label fw-bold fs-5">🔐 Confirmar Senha</label>
<input type="password" name="confirmar_senha" class="form-control form-control-lg" placeholder="Confirme nova senha" required>
</div>
<div class="d-grid gap-2 d-md-flex justify-content-end">
<a href="/" class="btn btn-secondary px-4">Cancelar</a>
<button type="submit" class="btn btn-info btn-lg px-5">
<i class="fas fa-key me-2"></i>Alterar Senha
</button>
</div>
</form>
</div>
</div>
</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

@app.post("/minha-conta/atualizar")
async def atualizar_minha_senha(request: Request, nova_senha: str = Form(...), confirmar_senha: str = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    if nova_senha != confirmar_senha:
        raise HTTPException(status_code=400, detail="Senhas não conferem!")
    
    if len(nova_senha) < 4:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 4 caracteres!")
    
    session_id = request.cookies.get("session_id", "")
    conn = get_db()
    usuario = conn.execute("SELECT id FROM usuarios WHERE session_id = ?", (session_id,)).fetchone()
    
    if not usuario:
        conn.close()
        raise HTTPException(status_code=401)
    
    hashed = hash_password(nova_senha)
    conn.execute("UPDATE usuarios SET password = ? WHERE id = ?", (hashed, usuario['id']))
    conn.commit()
    conn.close()
    
    return HTMLResponse(content="""
<!DOCTYPE html>
<html><head><title>Senha Alterada</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="bg-light">
<div class="container py-5 text-center">
<div class="alert alert-success">
<i class="fas fa-check-circle fa-3x mb-3 d-block"></i>
<h2>Senha alterada com sucesso!</h2>
<p class="lead">Faça login com sua nova senha.</p>
<a href="/login" class="btn btn-success btn-lg mt-3">Fazer Login</a>
</div>
</div>
</body></html>
    """)

#CRUD produtos
@app.get("/produtos", response_class=HTMLResponse)
async def produtos_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    produtos = conn.execute("""
        SELECT id, nome, quantidade, preco 
        FROM produtos 
        ORDER BY quantidade ASC
    """).fetchall()
    conn.close()
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head>
<title>📦 Produtos</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/" class="btn btn-outline-light me-2">← Dashboard</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-4">
<h1 class="mb-4"><i class="fas fa-boxes text-primary me-2"></i>Gerenciar Produtos</h1>

<!-- Form Novo Produto -->
<div class="card shadow mb-4">
<div class="card-header bg-success text-white">
<h5><i class="fas fa-plus me-2"></i>Novo Produto</h5>
</div>
<div class="card-body">
<form method="POST" action="/produtos/novo">
<div class="row">
<div class="col-md-4 mb-3">
<input name="nome" class="form-control" placeholder="Nome do produto" required>
</div>
<div class="col-md-3 mb-3">
<input name="quantidade" type="number" class="form-control" placeholder="0" min="0" required>
</div>
<div class="col-md-3 mb-3">
<input name="preco" type="number" step="0.01" class="form-control" placeholder="0.00" min="0" required>
</div>
<div class="col-md-2 mb-3">
<button class="btn btn-success w-100 py-2">➕ Criar</button>
</div>
</div>
</form>
</div>
</div>

<!-- Lista Produtos -->
<div class="card shadow">
<div class="card-header bg-primary text-white">
<h5><i class="fas fa-list me-2"></i>Produtos ({len(produtos)})</h5>
</div>
<div class="card-body p-0">
<div class="table-responsive">
<table class="table table-hover mb-0">
<thead class="table-dark">
<tr><th>Produto</th><th class="text-center">Estoque</th><th class="text-end">Preço</th><th class="text-center">Status</th><th>Ações</th></tr>
</thead>
<tbody>
""" + "".join([f"""
<tr>
<td><strong>{p['nome']}</strong></td>
<td class="text-center">
<span class="badge {'bg-success' if p['quantidade']>5 else 'bg-warning' if p['quantidade']>0 else 'bg-danger'}">
{p['quantidade']}
</span>
</td>
<td class="text-end"><strong>R$ {p['preco']:.2f}</strong></td>
<td class="text-center">
<span class="badge {'bg-success' if p['quantidade']>5 else 'bg-warning' if p['quantidade']>0 else 'bg-danger'}">
{'OK' if p['quantidade']>5 else 'POUCO' if p['quantidade']>0 else 'ESGOTADO'}
</span>
</td>
<td>
<a href="/produtos/editar/{p['id']}" class="btn btn-sm btn-primary me-1">
<i class="fas fa-edit"></i>
</a>
<form method="POST" action="/produtos/delete/{p['id']}" style="display:inline" 
onsubmit="return confirm('Excluir {p['nome']}?')">
<button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
</form>
</td>
</tr>
""" for p in produtos]) + """
</tbody>
</table>
</div>
</div>
</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

@app.post("/produtos/novo")
async def criar_produto(request: Request, nome: str = Form(...), quantidade: int = Form(...), preco: float = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    conn.execute("INSERT INTO produtos (nome, quantidade, preco) VALUES (?, ?, ?)", 
                (nome.strip(), quantidade, preco))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/produtos", status_code=303)

#LISTA DE PRODUTOS
@app.get("/produtos", response_class=HTMLResponse)
async def produtos_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    produtos = conn.execute("""
        SELECT id, nome, quantidade, preco 
        FROM produtos 
        ORDER BY nome
    """).fetchall()
    conn.close()
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head>
<title>📦 Produtos</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/" class="btn btn-outline-light me-2">← Dashboard</a>
<a href="/usuarios" class="btn btn-outline-light me-2">👥 Usuários</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-4">
<h1 class="mb-4"><i class="fas fa-boxes text-primary me-2"></i>Gerenciar Produtos</h1>

<!-- Form Novo Produto -->
<div class="card shadow mb-4">
<div class="card-header bg-success text-white">
<h5><i class="fas fa-plus me-2"></i>Novo Produto</h5>
</div>
<div class="card-body">
<form method="POST" action="/produtos/novo">
<div class="row">
<div class="col-md-4 mb-3">
<input name="nome" class="form-control" placeholder="Nome do produto" required>
</div>
<div class="col-md-3 mb-3">
<input name="quantidade" type="number" class="form-control" placeholder="0" min="0" required>
</div>
<div class="col-md-3 mb-3">
<input name="preco" type="number" step="0.01" class="form-control" placeholder="0.00" min="0" required>
</div>
<div class="col-md-2 mb-3">
<button class="btn btn-success w-100 py-2">➕ Criar</button>
</div>
</div>
</form>
</div>
</div>

<!-- Lista Produtos -->
<div class="card shadow">
<div class="card-header bg-primary text-white">
<h5><i class="fas fa-list me-2"></i>Produtos ({len(produtos)})</h5>
</div>
<div class="card-body p-0">
<div class="table-responsive">
<table class="table table-hover mb-0">
<thead class="table-dark">
<tr><th>ID</th><th>Produto</th><th class="text-center">Estoque</th><th class="text-end">Preço</th><th class="text-center">Ações</th></tr>
</thead>
<tbody>
""" + "".join([f"""
<tr>
<td><strong>#{p['id']}</strong></td>
<td>{p['nome']}</td>
<td class="text-center">
<span class="badge {'bg-success' if p['quantidade']>5 else 'bg-warning' if p['quantidade']>0 else 'bg-danger'}">
{p['quantidade']}
</span>
</td>
<td class="text-end"><strong>R$ {p['preco']:.2f}</strong></td>
<td class="text-center">
<a href="/produtos/editar/{p['id']}" class="btn btn-sm btn-primary me-1">
<i class="fas fa-edit"></i>
</a>
<form method="POST" action="/produtos/deletar/{p['id']}" style="display:inline" 
onsubmit="return confirm('Excluir {p['nome']}?')">
<button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
</form>
</td>
</tr>
""" for p in produtos]) + """
</tbody>
</table>
</div>
</div>
</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

#NOVO PRODUTO
@app.post("/produtos/novo")
async def criar_produto(request: Request, nome: str = Form(...), quantidade: int = Form(...), preco: float = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    conn.execute("INSERT INTO produtos (nome, quantidade, preco) VALUES (?, ?, ?)", 
                (nome.strip(), quantidade, preco))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/produtos", status_code=303)

@app.get("/produtos/editar/{produto_id}", response_class=HTMLResponse)
async def editar_produto(request: Request, produto_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    produto = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    conn.close()
    
    if not produto:
        return HTMLResponse(content="<h1>❌ Produto não encontrado!</h1><a href='/produtos'>Voltar</a>", status_code=404)
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head>
<title>✏️ Editar Produto</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/produtos" class="btn btn-outline-light me-2">← Produtos</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-5">
<div class="row justify-content-center">
<div class="col-md-6">
<div class="card shadow-lg">
<div class="card-header bg-warning text-dark">
<h4><i class="fas fa-edit me-2"></i>Editar Produto</h4>
</div>
<div class="card-body">
<form method="POST" action="/produtos/atualizar/{produto['id']}">
<div class="mb-3">
<label class="form-label fw-bold">📦 Nome</label>
<input type="text" name="nome" class="form-control form-control-lg" value="{produto['nome']}" required>
</div>
<div class="row">
<div class="col-md-6 mb-3">
<label class="form-label fw-bold">📊 Quantidade</label>
<input type="number" name="quantidade" class="form-control form-control-lg" value="{produto['quantidade']}" min="0" required>
</div>
<div class="col-md-6 mb-3">
<label class="form-label fw-bold">💰 Preço (R$)</label>
<input type="number" name="preco" step="0.01" class="form-control form-control-lg" value="{produto['preco']:.2f}" min="0" required>
</div>
</div>
<div class="d-grid gap-2 d-md-flex justify-content-end">
<a href="/produtos" class="btn btn-secondary px-4">Cancelar</a>
<button type="submit" class="btn btn-warning btn-lg px-5">
<i class="fas fa-save me-2"></i>Atualizar
</button>
</div>
</form>
</div>
</div>
</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

@app.post("/produtos/atualizar/{produto_id}")
async def atualizar_produto(request: Request, produto_id: int, nome: str = Form(...), 
                          quantidade: int = Form(...), preco: float = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    conn.execute("UPDATE produtos SET nome = ?, quantidade = ?, preco = ? WHERE id = ?", 
                (nome.strip(), quantidade, preco, produto_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/produtos", status_code=303)

@app.post("/produtos/deletar/{produto_id}")
async def deletar_produto(request: Request, produto_id: int):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    produto = conn.execute("SELECT nome FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not produto:
        conn.close()
        raise HTTPException(status_code=404)
    
    conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/produtos", status_code=303)

#EMPRESAS
@app.get("/empresas", response_class=HTMLResponse)
async def empresas_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    empresas = conn.execute("""
        SELECT id, cnpj, razao_social, nome_fantasia, email, ativo 
        FROM empresas 
        WHERE ativo = 1
        ORDER BY razao_social
    """).fetchall()
    conn.close()
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head>
<title>🏢 Empresas</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/" class="btn btn-outline-light me-2">← Dashboard</a>
<a href="/produtos" class="btn btn-outline-light me-2">📦 Produtos</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-4">
<h1 class="mb-4"><i class="fas fa-building text-success me-2"></i>Gerenciar Empresas</h1>

<!-- Form Nova Empresa -->
<div class="card shadow mb-4">
<div class="card-header bg-success text-white">
<h5><i class="fas fa-plus me-2"></i>Nova Empresa</h5>
</div>
<div class="card-body">
<form method="POST" action="/empresas/nova">
<div class="row">
<div class="col-md-3 mb-3">
<input name="cnpj" class="form-control" placeholder="00.000.000/0001-00" maxlength="18" required>
</div>
<div class="col-md-4 mb-3">
<input name="razao_social" class="form-control" placeholder="Razão Social" required>
</div>
<div class="col-md-3 mb-3">
<input name="nome_fantasia" class="form-control" placeholder="Nome Fantasia">
</div>
<div class="col-md-2 mb-3">
<button class="btn btn-success w-100 py-2">➕ Criar</button>
</div>
</div>
</form>
</div>
</div>

<!-- Lista Empresas -->
<div class="card shadow">
<div class="card-header bg-success text-white">
<h5><i class="fas fa-list me-2"></i>Empresas ({len(empresas)})</h5>
</div>
<div class="card-body p-0">
<div class="table-responsive">
<table class="table table-hover mb-0">
<thead class="table-dark">
<tr><th>CNPJ</th><th>Razão Social</th><th>Fantasia</th><th>Email</th><th>Status</th><th>Ações</th></tr>
</thead>
<tbody>
""" + "".join([f"""
<tr>
<td><strong>{e['cnpj']}</strong></td>
<td>{e['razao_social']}</td>
<td>{e['nome_fantasia'] or '-'}</td>
<td>{e['email'] or '-'}</td>
<td class="text-center">
<span class="badge {'bg-success' if e['ativo'] else 'bg-secondary'}">
{'Ativa' if e['ativo'] else 'Inativa'}
</span>
</td>
<td>
<a href="/empresas/editar/{e['id']}" class="btn btn-sm btn-primary me-1"><i class="fas fa-edit"></i></a>
<form method="POST" action="/empresas/deletar/{e['id']}" style="display:inline" 
onsubmit="return confirm('Excluir {e['razao_social']}?')">
<button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
</form>
</td>
</tr>
""" for e in empresas]) + """
</tbody>
</table>
</div>
</div>
</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

@app.post("/empresas/nova")
async def criar_empresa(request: Request, cnpj: str = Form(...), razao_social: str = Form(...), 
                       nome_fantasia: str = Form(None), email: str = Form(None)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    # Limpa formatação CNPJ
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    
    conn = get_db()
    try:
        conn.execute("INSERT INTO empresas (cnpj, razao_social, nome_fantasia, email) VALUES (?, ?, ?, ?)", 
                    (cnpj_limpo, razao_social.strip(), nome_fantasia, email))
        conn.commit()
    except sqlite3.IntegrityError:
        return HTMLResponse(content="❌ CNPJ já cadastrado!", status_code=400)
    conn.close()
    return RedirectResponse(url="/empresas", status_code=303)

@app.get("/empresas/editar/{empresa_id}", response_class=HTMLResponse)
async def editar_empresa(request: Request, empresa_id: int):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    
    conn = get_db()
    empresa = conn.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    conn.close()
    
    if not empresa:
        return HTMLResponse(content="<h1>❌ Empresa não encontrada!</h1><a href='/empresas'>Voltar</a>", status_code=404)
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><head>
<title>✏️ Editar Empresa</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head><body class="bg-light">
<nav class="navbar navbar-dark bg-primary">
<div class="container">
<a class="navbar-brand" href="/">📦 Estoque MEI</a>
<a href="/empresas" class="btn btn-outline-light me-2">← Empresas</a>
<a href="/logout/" class="btn btn-outline-light">Sair</a>
</div>
</nav>
<div class="container py-5">
<div class="row justify-content-center">
<div class="col-md-8">
<div class="card shadow-lg">
<div class="card-header bg-warning text-dark">
<h4><i class="fas fa-edit me-2"></i>Editar Empresa</h4>
</div>
<div class="card-body">
<form method="POST" action="/empresas/atualizar/{empresa['id']}">
<div class="row">
<div class="col-md-3 mb-3">
<label class="form-label fw-bold">🏢 CNPJ</label>
<input type="text" name="cnpj" class="form-control form-control-lg" value="{empresa['cnpj']}" required>
</div>
<div class="col-md-4 mb-3">
<label class="form-label fw-bold">📝 Razão Social</label>
<input type="text" name="razao_social" class="form-control form-control-lg" value="{empresa['razao_social']}" required>
</div>
<div class="col-md-3 mb-3">
<label class="form-label fw-bold">🏪 Nome Fantasia</label>
<input type="text" name="nome_fantasia" class="form-control form-control-lg" value="{empresa['nome_fantasia'] or ''}">
</div>
<div class="col-md-2 mb-3">
<label class="form-label fw-bold">✉️ Email</label>
<input type="email" name="email" class="form-control form-control-lg" value="{empresa['email'] or ''}">
</div>
</div>
<div class="d-grid gap-2 d-md-flex justify-content-end">
<a href="/empresas" class="btn btn-secondary px-4">Cancelar</a>
<button type="submit" class="btn btn-warning btn-lg px-5">
<i class="fas fa-save me-2"></i>Atualizar
</button>
</div>
</form>
</div>
</div>
</div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
    """)

@app.post("/empresas/atualizar/{empresa_id}")
async def atualizar_empresa(request: Request, empresa_id: int, cnpj: str = Form(...), 
                          razao_social: str = Form(...), nome_fantasia: str = Form(None), 
                          email: str = Form(None)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    
    conn = get_db()
    conn.execute("""
        UPDATE empresas SET cnpj = ?, razao_social = ?, nome_fantasia = ?, email = ? 
        WHERE id = ?""", (cnpj_limpo, razao_social.strip(), nome_fantasia, email, empresa_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/empresas", status_code=303)

@app.post("/empresas/deletar/{empresa_id}")
async def deletar_empresa(request: Request, empresa_id: int):
    if not is_authenticated(request):
        raise HTTPException(status_code=401)
    
    conn = get_db()
    conn.execute("DELETE FROM empresas WHERE id = ?", (empresa_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/empresas", status_code=303)
