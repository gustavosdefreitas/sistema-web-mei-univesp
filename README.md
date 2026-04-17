# Sistema de Controle de Estoque Multi-Empresa 📦

Projeto desenvolvido para a disciplina de **Projeto Integrador I** da [Univesp](https://univesp.br). O sistema permite o gerenciamento de estoque, vendas, fornecedores e usuários para múltiplas empresas em uma única interface.

## 🚀 Requisitos Atendidos (Checklist Univesp)

- **Framework Web:** Desenvolvido com **FastAPI** (Python)
- **Banco de Dados:** **SQLite** com relacionamentos entre Empresas, Produtos, Fornecedores e Vendas
- **Script Web (JS):** Gráficos dinâmicos com **Chart.js**
- **Nuvem:** Preparado para deploy em plataformas como Render/Railway
- **Acessibilidade:** Tags semânticas HTML5, atributos ARIA e alto contraste via Bootstrap 5
- **Controle de Versão:** Repositório gerenciado via **Git/GitHub**
- **Integração Contínua (CI):** Workflow no **GitHub Actions** com instalação via `requirements.txt`
- **Testes Unitários:** Suite de 30 testes automatizados com **Pytest** e banco em memória
- **Análise de Dados:** Dashboard com indicadores de desempenho e gráfico de distribuição de estoque
- **API:** Endpoint `/api/produtos/{empresa_id}` retorna estoque em JSON

## 🛠️ Tecnologias Utilizadas

- Python 3.10+
- FastAPI & Uvicorn
- Jinja2 (Templates)
- SQLite
- Bootstrap 5 & Chart.js
- bcrypt (hashing de senhas)
- python-dotenv (configurações via `.env`)
- Pytest & HTTPX (testes)

## ⚙️ Configuração do ambiente

Copie o arquivo `.env.example` para `.env` e preencha os valores:

```bash
cp .env.example .env
```

Variáveis disponíveis:

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `estoque.db` | Caminho para o arquivo SQLite |
| `ADMIN_PASSWORD` | _(obrigatório)_ | Senha do usuário admin (usada pelo `reset_sistema.py`) |
| `ENVIRONMENT` | `development` | `development` ou `production` — em produção o cookie exige HTTPS |

> **Importante:** o arquivo `.env` nunca deve ser commitado. Ele já está no `.gitignore`.

## 🗄️ Inicializar o banco de dados

Para criar o banco pela primeira vez com dados de exemplo:

```bash
python init_db.py
```

Para apagar tudo e recriar do zero (requer `ADMIN_PASSWORD` no `.env`):

```bash
python reset_sistema.py
```

## ▶️ Como rodar

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Acesse em: [http://localhost:8000](http://localhost:8000)

Login padrão (após `init_db.py`): **admin** / **admin123** *(troque em produção)*

## 🧪 Como rodar os testes

```bash
python -m pytest test_main.py -v
```

Os testes usam banco SQLite em memória — não afetam o banco de dados local.

## 📁 Estrutura do projeto

```
├── main.py               # Aplicação FastAPI (rotas, lógica, dependências)
├── init_db.py            # Inicializa o banco com schema completo e dados de exemplo
├── reset_sistema.py      # Apaga e recria o banco do zero
├── test_main.py          # Suite de testes (30 testes)
├── requirements.txt      # Dependências do projeto
├── .env.example          # Modelo de variáveis de ambiente
├── templates/            # Templates Jinja2 (HTML)
├── static/               # Arquivos estáticos (CSS)
└── .github/workflows/    # CI — GitHub Actions
```

## 🔒 Segurança

- Senhas com hash **bcrypt** (salt automático)
- Cookie de sessão com `httponly`, `samesite=lax` e `secure` (em produção)
- Todas as operações de escrita protegidas por autenticação
- Deleções via `POST` (proteção contra CSRF)
- Configurações sensíveis em variáveis de ambiente (nunca hardcoded)
