# KiPão

Sistema web de gestão para padaria, feito em Flask: controle de insumos e produtos,
receitas (ficha técnica), compras com custo médio, produção com baixa automática de
insumos, PDV com comprovante, registro de perdas e relatórios de vendas, compras e
desperdício.

## Tecnologias

- Python 3.12 + Flask 3
- Flask-SQLAlchemy (SQLite por padrão; MySQL opcional)
- Flask-Login (perfis ADMIN e FUNCIONARIO)
- Bootstrap nos templates

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

Acesse http://127.0.0.1:5000. Na primeira execução o sistema cria as tabelas e um
usuário administrador de teste:

- e-mail: `admin@kipao.local`
- senha: `admin123`

Troque essa senha em qualquer instalação que não seja de teste.

## Configuração

| Variável       | Padrão                  | Para que serve                         |
|----------------|-------------------------|----------------------------------------|
| `SECRET_KEY`   | valor de desenvolvimento | Chave das sessões do Flask             |
| `DATABASE_URL` | `sqlite:///kipao.db`    | Banco; ex.: `mysql+pymysql://usuario:senha@host/kipao` |

Para MySQL, veja `database_mysql.sql`.
