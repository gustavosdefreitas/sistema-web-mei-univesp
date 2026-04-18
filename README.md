# Estoque Fácil MEI 📦

Sistema web de controle de estoque desenvolvido para a disciplina de **Projeto Integrador** da [Univesp](https://univesp.br). Permite o gerenciamento completo de estoque, vendas, fornecedores, empresas e usuários em uma única interface.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)
![Testes](https://img.shields.io/badge/testes-47%20passando-brightgreen?logo=pytest)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions)

---

## ✅ Requisitos Atendidos (Checklist Univesp)

| Requisito | Implementação |
|---|---|
| Framework Web | **FastAPI** (Python) |
| Banco de Dados | **SQLite** com relacionamentos entre 5 tabelas |
| Script Web (JS) | Gráficos dinâmicos com **Chart.js**, busca em tempo real, máscara de CPF/CNPJ |
| Integração de API externa | Consulta CNPJ via **BrasilAPI** (Receita Federal) |
| Nuvem | Preparado para deploy em Render/Railway |
| Acessibilidade | HTML5 semântico, atributos ARIA, alto contraste via Bootstrap 5 |
| Controle de Versão | Repositório **Git/GitHub** com histórico de +40 PRs |
| Integração Contínua (CI) | Workflow **GitHub Actions** automatizado |
| Testes Unitários | **47 testes** com Pytest e banco SQLite em memória |
| Análise de Dados | Dashboard com KPIs, gráfico de estoque e produto mais vendido |
| API REST | Endpoint `/api/produtos/{empresa_id}` com autenticação |

---

## 🚀 Funcionalidades

### Dashboard
- Cards KPI: total de itens em estoque, vendas, fornecedores e empresas
- Card de valor total do estoque (R$)
- Produto mais vendido do período
- Gráfico de distribuição de estoque por empresa
- Tabela de vendas recentes com datas formatadas em pt-BR

### Produtos
- Cadastro, edição e exclusão de produtos
- Busca em tempo real por nome, empresa ou fornecedor
- Badge de alerta: 🔴 Estoque Baixo (≤ 5 unidades) e 🟡 Atenção (≤ 10 unidades)
- Confirmação de exclusão via diálogo

### Vendas
- Registro de vendas com validação de quantidade disponível
- Rodapé com total acumulado em R$
- Datas exibidas em formato pt-BR (dd/mm/aaaa hh:mm)

### Fornecedores
- Consulta automática de CNPJ via Receita Federal (BrasilAPI)
- Preenchimento automático de nome, telefone e e-mail
- Exibição da **situação cadastral** (ATIVA, INAPTA, SUSPENSA, BAIXADA) com badge colorido
- Apenas o CNPJ é obrigatório no cadastro

### Empresas
- Consulta automática de CNPJ via Receita Federal (BrasilAPI)
- Preenchimento automático de nome fantasia e razão social
- Exibição da **situação cadastral** com badge colorido e data de vigência
- Apenas o CNPJ é obrigatório no cadastro

### Usuários
- Cadastro com: login de acesso, nome completo, CPF (com máscara), perfil e senha
- Perfis: **Administrador** (acesso total) e **Operador** (acesso restrito)
- Badge de perfil por cor na listagem

### Segurança
- Senhas com hash **bcrypt** (salt automático)
- Cookie de sessão: `httponly`, `samesite=lax`, `secure` (em produção via HTTPS)
- Todas as rotas protegidas por autenticação
- Deleções via `POST` (proteção contra CSRF)
- API `/api/produtos/{empresa_id}` protegida por autenticação
- Configurações sensíveis em variáveis de ambiente (nunca hardcoded)

---

## 🛠️ Tecnologias

| Categoria | Tecnologia |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Templates | Jinja2 |
| Banco de dados | SQLite |
| Frontend | Bootstrap 5, Chart.js, JavaScript puro |
| Segurança | bcrypt, python-dotenv |
| Testes | Pytest, HTTPX |
| CI | GitHub Actions |
| API externa | BrasilAPI (CNPJ / Receita Federal) |

---

## ⚙️ Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/gustavosdefreitas/sistema-web-mei-univesp.git
cd sistema-web-mei-univesp
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure o ambiente

Copie `.env.example` para `.env` e preencha os valores:

```bash
cp .env.example .env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `estoque.db` | Caminho para o arquivo SQLite |
| `ADMIN_PASSWORD` | `admin123` | Senha do usuário admin |
| `ENVIRONMENT` | `development` | `production` exige HTTPS para o cookie de sessão |

> **Atenção:** o arquivo `.env` nunca deve ser commitado — já está no `.gitignore`.

### 4. Inicialize o banco de dados

```bash
python init_db.py
```

Para apagar tudo e recriar do zero:

```bash
python reset_sistema.py
```

### 5. Execute a aplicação

```bash
uvicorn main:app --reload
```

Acesse em: [http://localhost:8000](http://localhost:8000)

**Login padrão:** `admin` / `admin123` *(altere em produção via `ADMIN_PASSWORD` no `.env`)*

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
python -m pytest test_main.py -v
```

- **47 testes** cobrindo autenticação, rotas, validações, deleções, bcrypt e sessões
- Banco SQLite em memória isolado por teste — não afeta dados locais
- Executados automaticamente pelo GitHub Actions em cada push

---

## 📁 Estrutura do Projeto

```
├── main.py                  # Aplicação FastAPI (rotas, lógica, dependências)
├── init_db.py               # Inicializa o banco com schema completo e dados de exemplo
├── reset_sistema.py         # Apaga e recria o banco do zero
├── test_main.py             # 47 testes automatizados
├── requirements.txt         # Dependências de produção
├── requirements-dev.txt     # Dependências de desenvolvimento/testes
├── .env.example             # Modelo de variáveis de ambiente
├── templates/
│   ├── base.html            # Layout base (navbar, flash messages)
│   ├── login.html
│   ├── dashboard.html       # KPIs, gráfico e vendas recentes
│   ├── produtos.html        # Listagem com busca e alertas de estoque
│   ├── cadastrar_produto.html
│   ├── editar_produto.html
│   ├── vendas.html
│   ├── fornecedores.html    # CNPJ lookup + situação cadastral
│   ├── empresas.html        # CNPJ lookup + situação cadastral
│   ├── editar_empresa.html
│   ├── usuarios.html        # Cadastro com CPF, nome completo e perfil
│   └── editar_usuario.html
├── static/
│   └── style.css
└── .github/
    └── workflows/
        └── python-app.yaml  # CI — instala deps, roda testes
```

---

## 🗂️ Histórico de PRs

| PR | Descrição |
|---|---|
| #14 | Remove `.db` e `__pycache__` do rastreamento Git |
| #15 | Deleções GET→POST + proteção CSRF |
| #16 | Remove senha hardcoded, adiciona `.env.example` |
| #17 | Cookie de sessão seguro (`samesite=lax`, `secure`) |
| #18 | Hash de senhas SHA-256 → bcrypt direto |
| #19 | Conexões com banco via `Depends`/`yield` |
| #20 | 17 testes automatizados + fix warning Jinja2 |
| #21 | Centraliza configurações em `.env` |
| #22 | `init_db.py` sincronizado com o schema real |
| #23 | Valida quantidade na venda (sem estoque negativo) |
| #24 | CI usa `requirements.txt` corretamente |
| #25 | Padronização das rotas REST |
| #30 | Correção de 4 bugs críticos (logout, templates, fornecedor) |
| #31 | Autenticação em 3 rotas desprotegidas |
| #32 | README inicial |
| #33 | Limpeza de dependências e scripts temporários |
| #34 | Testes para rotas `/empresas/deletar` e `/fornecedores/editar` |
| #35 | `check_same_thread=False` no SQLite |
| #36 | Remove item "Dashboard" duplicado da navbar |
| #37 | Corrige layout do dashboard + adiciona card Empresas |
| #38 | Badge estoque baixo + total de vendas + auth na API |
| #39 | Datas em pt-BR + card valor total do estoque |
| #40 | Flash messages + busca em tempo real + confirmação de exclusão |
| #41 | Produto mais vendido no dashboard |
| #42 | 47 testes cobrindo PRs #15, #17 e #18 |
| #43 | Consulta CNPJ via BrasilAPI em fornecedores e empresas |
| #44 | Campos completos no cadastro de usuário (CPF, nome, perfil) |
| #45 | Situação cadastral da Receita Federal em empresas e fornecedores |
| #46 | Apenas CNPJ obrigatório no cadastro de empresas e fornecedores |
