"""Testes de fumaça do KiPão: o app sobe, o login funciona e todas as telas abrem.

Rodam no GitHub Actions antes de cada deploy no Coolify.
Para rodar no PC:  pip install -r requirements-dev.txt  e  pytest
"""
import os
import sys
import tempfile

import pytest

# Banco SQLite temporário, separado do banco de verdade
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "teste.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "chave-de-teste"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app  # noqa: E402

TELAS_ADMIN = [
    "/", "/usuarios", "/fornecedores", "/insumos", "/produtos", "/receitas",
    "/formas-pagamento", "/compras", "/producao", "/pdv", "/perdas",
    "/relatorios/vendas", "/relatorios/compras", "/relatorios/desperdicio",
]


@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def login_admin(c):
    return c.post("/login", data={"email": "admin@kipao.local", "senha": "admin123"})


def test_tela_de_login_abre(cliente):
    r = cliente.get("/login")
    assert r.status_code == 200
    assert "Ki-Pão" in r.get_data(as_text=True)


def test_sem_login_redireciona_para_login(cliente):
    r = cliente.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_login_com_senha_errada_falha(cliente):
    r = cliente.post("/login", data={"email": "admin@kipao.local", "senha": "errada"})
    assert r.status_code == 200
    assert "Credenciais inválidas" in r.get_data(as_text=True)


def test_login_admin_funciona(cliente):
    r = login_admin(cliente)
    assert r.status_code == 302


@pytest.mark.parametrize("url", TELAS_ADMIN)
def test_telas_do_admin_abrem(cliente, url):
    login_admin(cliente)
    r = cliente.get(url)
    assert r.status_code == 200, f"{url} retornou {r.status_code}"
