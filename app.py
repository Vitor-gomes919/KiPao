from __future__ import annotations

import os
from datetime import datetime, date
from decimal import Decimal

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, abort
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
# Atrás do proxy do Coolify (HTTPS), respeita os cabeçalhos X-Forwarded-*
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "kipao-dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL") or "sqlite:///kipao.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para continuar."
login_manager.login_message_category = "warning"


# ==========================================================
# MODELOS
# ==========================================================

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="FUNCIONARIO")
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def conferir_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_active(self):
        return self.ativo

    @property
    def admin(self):
        return self.perfil == "ADMIN"


class Fornecedor(db.Model):
    __tablename__ = "fornecedor"

    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(150), nullable=False)
    documento = db.Column(db.String(30), unique=True, nullable=False)
    telefone = db.Column(db.String(30))
    email = db.Column(db.String(150))
    endereco = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, nullable=False, default=True)


class Insumo(db.Model):
    __tablename__ = "insumo"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    categoria = db.Column(db.String(80))
    unidade_medida = db.Column(db.String(30), nullable=False)
    qtd_atual = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    qtd_minima = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    custo_medio = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def critico(self):
        return Decimal(self.qtd_atual or 0) <= Decimal(self.qtd_minima or 0)


class Produto(db.Model):
    __tablename__ = "produto_acabado"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    categoria = db.Column(db.String(80))
    preco_venda = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    qtd_atual = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    qtd_minima = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    custo_estimado = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def critico(self):
        return Decimal(self.qtd_atual or 0) <= Decimal(self.qtd_minima or 0)


class Receita(db.Model):
    __tablename__ = "receita"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto_acabado.id"), unique=True, nullable=False)
    rendimento = db.Column(db.Numeric(12, 3), nullable=False, default=1)

    produto = db.relationship("Produto", backref=db.backref("receita", uselist=False, cascade="all, delete-orphan"))


class ItemReceita(db.Model):
    __tablename__ = "item_receita"

    id = db.Column(db.Integer, primary_key=True)
    receita_id = db.Column(db.Integer, db.ForeignKey("receita.id"), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumo.id"), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)

    receita = db.relationship("Receita", backref=db.backref("itens", cascade="all, delete-orphan"))
    insumo = db.relationship("Insumo")


class FormaPagamento(db.Model):
    __tablename__ = "forma_pagamento"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(60), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)


class Compra(db.Model):
    __tablename__ = "compra"

    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("fornecedor.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    fornecedor = db.relationship("Fornecedor")
    usuario = db.relationship("Usuario")


class ItemCompra(db.Model):
    __tablename__ = "item_compra"

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compra.id"), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumo.id"), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    preco_unitario = db.Column(db.Numeric(12, 2), nullable=False)

    compra = db.relationship("Compra", backref=db.backref("itens", cascade="all, delete-orphan"))
    insumo = db.relationship("Insumo")


class Producao(db.Model):
    __tablename__ = "producao"

    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto_acabado.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)
    qtd_produzida = db.Column(db.Numeric(12, 3), nullable=False)

    produto = db.relationship("Produto")
    usuario = db.relationship("Usuario")


class ItemProducao(db.Model):
    __tablename__ = "item_producao"

    id = db.Column(db.Integer, primary_key=True)
    producao_id = db.Column(db.Integer, db.ForeignKey("producao.id"), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumo.id"), nullable=False)
    quantidade_usada = db.Column(db.Numeric(12, 3), nullable=False)

    producao = db.relationship("Producao", backref=db.backref("itens", cascade="all, delete-orphan"))
    insumo = db.relationship("Insumo")


class Venda(db.Model):
    __tablename__ = "venda"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    forma_pagamento_id = db.Column(db.Integer, db.ForeignKey("forma_pagamento.id"), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)
    valor_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    usuario = db.relationship("Usuario")
    forma_pagamento = db.relationship("FormaPagamento")


class ItemVenda(db.Model):
    __tablename__ = "item_venda"

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey("venda.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto_acabado.id"), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    preco_unitario = db.Column(db.Numeric(12, 2), nullable=False)

    venda = db.relationship("Venda", backref=db.backref("itens", cascade="all, delete-orphan"))
    produto = db.relationship("Produto")


class Perda(db.Model):
    __tablename__ = "perda"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    tipo_item = db.Column(db.String(20), nullable=False)  # INSUMO ou PRODUTO
    item_id = db.Column(db.Integer, nullable=False)
    nome_item = db.Column(db.String(120), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    motivo = db.Column(db.String(50), nullable=False)
    custo_unitario = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.now)

    usuario = db.relationship("Usuario")

    @property
    def valor_perda(self):
        return Decimal(self.quantidade or 0) * Decimal(self.custo_unitario or 0)


# ==========================================================
# AUTENTICAÇÃO / UTILITÁRIOS
# ==========================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def admin_required():
    if not current_user.is_authenticated or not current_user.admin:
        abort(403)


def decimal_form(nome, default=0):
    valor = (request.form.get(nome) or "").strip().replace(",", ".")
    if valor == "":
        return Decimal(str(default))
    return Decimal(valor)


@app.template_filter("moeda")
def moeda(valor):
    v = Decimal(valor or 0)
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


@app.template_filter("numero")
def numero(valor):
    v = Decimal(valor or 0)
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


@app.context_processor
def globals_template():
    return {"agora": datetime.now()}


# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario or not usuario.ativo or not usuario.conferir_senha(senha):
            flash("Credenciais inválidas.", "danger")
            return render_template("login.html")

        login_user(usuario)
        flash(f"Bem-vindo, {usuario.nome}!", "success")
        if usuario.admin:
            return redirect(url_for("index"))
        return redirect(url_for("pdv"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ==========================================================
# DASHBOARD
# ==========================================================

@app.route("/")
@login_required
def index():
    if not current_user.admin:
        return redirect(url_for("pdv"))

    hoje = date.today()
    vendas_hoje = Venda.query.filter(func.date(Venda.data_hora) == hoje).all()
    faturamento = sum((Decimal(v.valor_total or 0) for v in vendas_hoje), Decimal("0"))
    insumos_criticos = [x for x in Insumo.query.filter_by(ativo=True).all() if x.critico]
    produtos_criticos = [x for x in Produto.query.filter_by(ativo=True).all() if x.critico]
    perdas_hoje = Perda.query.filter(func.date(Perda.data_hora) == hoje).all()
    desperdicio = sum((p.valor_perda for p in perdas_hoje), Decimal("0"))

    return render_template(
        "dashboard.html",
        vendas_hoje=len(vendas_hoje),
        faturamento=faturamento,
        insumos_criticos=insumos_criticos,
        produtos_criticos=produtos_criticos,
        desperdicio=desperdicio,
    )


# ==========================================================
# USUÁRIOS
# ==========================================================

@app.route("/usuarios", methods=["GET", "POST"])
@login_required
def usuarios():
    admin_required()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        perfil = request.form["perfil"]

        if Usuario.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
        elif not nome or not senha:
            flash("Preencha os campos obrigatórios.", "danger")
        else:
            u = Usuario(nome=nome, email=email, perfil=perfil, ativo=True)
            u.set_senha(senha)
            db.session.add(u)
            db.session.commit()
            flash("Usuário cadastrado.", "success")
            return redirect(url_for("usuarios"))

    return render_template("usuarios.html", usuarios=Usuario.query.order_by(Usuario.nome).all())


@app.post("/usuarios/<int:id>/toggle")
@login_required
def usuario_toggle(id):
    admin_required()
    u = db.get_or_404(Usuario, id)
    if u.id == current_user.id:
        flash("Você não pode inativar o próprio usuário durante a sessão.", "warning")
    else:
        u.ativo = not u.ativo
        db.session.commit()
        flash("Status do usuário alterado.", "success")
    return redirect(url_for("usuarios"))


# ==========================================================
# FORNECEDORES
# ==========================================================

@app.route("/fornecedores", methods=["GET", "POST"])
@login_required
def fornecedores():
    admin_required()

    if request.method == "POST":
        documento = request.form["documento"].strip()
        if Fornecedor.query.filter_by(documento=documento).first():
            flash("CNPJ/CPF já cadastrado.", "danger")
        else:
            f = Fornecedor(
                razao_social=request.form["razao_social"].strip(),
                documento=documento,
                telefone=request.form.get("telefone", "").strip(),
                email=request.form.get("email", "").strip(),
                endereco=request.form.get("endereco", "").strip(),
            )
            db.session.add(f)
            db.session.commit()
            flash("Fornecedor cadastrado.", "success")
            return redirect(url_for("fornecedores"))

    return render_template("fornecedores.html", fornecedores=Fornecedor.query.order_by(Fornecedor.razao_social).all())


@app.post("/fornecedores/<int:id>/toggle")
@login_required
def fornecedor_toggle(id):
    admin_required()
    f = db.get_or_404(Fornecedor, id)
    f.ativo = not f.ativo
    db.session.commit()
    return redirect(url_for("fornecedores"))


# ==========================================================
# INSUMOS
# ==========================================================

@app.route("/insumos", methods=["GET", "POST"])
@login_required
def insumos():
    admin_required()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        if Insumo.query.filter(func.lower(Insumo.nome) == nome.lower()).first():
            flash("Já existe um insumo com esse nome.", "danger")
        else:
            item = Insumo(
                nome=nome,
                categoria=request.form.get("categoria", "").strip(),
                unidade_medida=request.form["unidade_medida"].strip(),
                qtd_minima=decimal_form("qtd_minima"),
                qtd_atual=0,
            )
            db.session.add(item)
            db.session.commit()
            flash("Insumo cadastrado.", "success")
            return redirect(url_for("insumos"))

    return render_template("insumos.html", insumos=Insumo.query.order_by(Insumo.nome).all())


@app.post("/insumos/<int:id>/toggle")
@login_required
def insumo_toggle(id):
    admin_required()
    item = db.get_or_404(Insumo, id)
    item.ativo = not item.ativo
    db.session.commit()
    return redirect(url_for("insumos"))


# ==========================================================
# PRODUTOS
# ==========================================================

@app.route("/produtos", methods=["GET", "POST"])
@login_required
def produtos():
    admin_required()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        if Produto.query.filter(func.lower(Produto.nome) == nome.lower()).first():
            flash("Já existe um produto com esse nome.", "danger")
        else:
            p = Produto(
                nome=nome,
                categoria=request.form.get("categoria", "").strip(),
                preco_venda=decimal_form("preco_venda"),
                qtd_minima=decimal_form("qtd_minima"),
                qtd_atual=0,
            )
            db.session.add(p)
            db.session.commit()
            flash("Produto cadastrado.", "success")
            return redirect(url_for("produtos"))

    return render_template("produtos.html", produtos=Produto.query.order_by(Produto.nome).all())


@app.post("/produtos/<int:id>/toggle")
@login_required
def produto_toggle(id):
    admin_required()
    p = db.get_or_404(Produto, id)
    p.ativo = not p.ativo
    db.session.commit()
    return redirect(url_for("produtos"))


# ==========================================================
# RECEITAS
# ==========================================================

@app.route("/receitas")
@login_required
def receitas():
    admin_required()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    return render_template("receitas.html", produtos=produtos)


@app.route("/receitas/<int:produto_id>", methods=["GET", "POST"])
@login_required
def receita_editar(produto_id):
    admin_required()
    produto = db.get_or_404(Produto, produto_id)
    receita = Receita.query.filter_by(produto_id=produto.id).first()

    if request.method == "POST":
        if not receita:
            receita = Receita(produto=produto)
            db.session.add(receita)
            db.session.flush()

        receita.rendimento = decimal_form("rendimento", 1)
        ItemReceita.query.filter_by(receita_id=receita.id).delete()

        insumo_ids = request.form.getlist("insumo_id")
        quantidades = request.form.getlist("quantidade")
        for insumo_id, quantidade in zip(insumo_ids, quantidades):
            if not insumo_id or not quantidade.strip():
                continue
            q = Decimal(quantidade.replace(",", "."))
            if q <= 0:
                continue
            db.session.add(ItemReceita(
                receita_id=receita.id,
                insumo_id=int(insumo_id),
                quantidade=q
            ))

        db.session.commit()
        atualizar_custo_produto(produto)
        db.session.commit()
        flash("Receita atualizada.", "success")
        return redirect(url_for("receitas"))

    return render_template(
        "receita_editar.html",
        produto=produto,
        receita=receita,
        insumos=Insumo.query.filter_by(ativo=True).order_by(Insumo.nome).all()
    )


def atualizar_custo_produto(produto):
    if not produto.receita or Decimal(produto.receita.rendimento or 0) <= 0:
        produto.custo_estimado = 0
        return
    custo = Decimal("0")
    for item in produto.receita.itens:
        custo += Decimal(item.quantidade) * Decimal(item.insumo.custo_medio or 0)
    produto.custo_estimado = custo / Decimal(produto.receita.rendimento)


# ==========================================================
# FORMAS DE PAGAMENTO
# ==========================================================

@app.route("/formas-pagamento", methods=["GET", "POST"])
@login_required
def formas_pagamento():
    admin_required()

    if request.method == "POST":
        ativos = {int(x) for x in request.form.getlist("ativo")}
        if not ativos:
            flash("Selecione ao menos uma forma de pagamento.", "danger")
        else:
            for forma in FormaPagamento.query.all():
                forma.ativo = forma.id in ativos
            db.session.commit()
            flash("Formas de pagamento atualizadas.", "success")
            return redirect(url_for("formas_pagamento"))

    return render_template("formas_pagamento.html", formas=FormaPagamento.query.order_by(FormaPagamento.nome).all())


# ==========================================================
# COMPRAS
# ==========================================================

@app.route("/compras", methods=["GET", "POST"])
@login_required
def compras():
    admin_required()

    if request.method == "POST":
        fornecedor_id = int(request.form["fornecedor_id"])
        fornecedor = db.get_or_404(Fornecedor, fornecedor_id)

        insumo_ids = request.form.getlist("insumo_id")
        quantidades = request.form.getlist("quantidade")
        precos = request.form.getlist("preco_unitario")

        itens_validos = []
        total = Decimal("0")

        for insumo_id, qtd, preco in zip(insumo_ids, quantidades, precos):
            if not insumo_id or not qtd.strip() or not preco.strip():
                continue
            insumo = db.session.get(Insumo, int(insumo_id))
            q = Decimal(qtd.replace(",", "."))
            p = Decimal(preco.replace(",", "."))
            if not insumo or q <= 0 or p < 0:
                continue
            itens_validos.append((insumo, q, p))
            total += q * p

        if not itens_validos:
            flash("Adicione pelo menos um insumo à compra.", "danger")
        else:
            try:
                compra = Compra(
                    fornecedor=fornecedor,
                    usuario=current_user,
                    valor_total=total
                )
                db.session.add(compra)
                db.session.flush()

                for insumo, q, p in itens_validos:
                    saldo_anterior = Decimal(insumo.qtd_atual or 0)
                    custo_anterior = Decimal(insumo.custo_medio or 0)
                    novo_saldo = saldo_anterior + q

                    if novo_saldo > 0:
                        insumo.custo_medio = (
                            (saldo_anterior * custo_anterior) + (q * p)
                        ) / novo_saldo
                    insumo.qtd_atual = novo_saldo

                    db.session.add(ItemCompra(
                        compra=compra,
                        insumo=insumo,
                        quantidade=q,
                        preco_unitario=p,
                    ))

                # Recalcula custo estimado de produtos
                for produto in Produto.query.all():
                    atualizar_custo_produto(produto)

                db.session.commit()
                flash("Compra registrada e estoque atualizado.", "success")
                return redirect(url_for("compras"))
            except Exception:
                db.session.rollback()
                raise

    historico = Compra.query.order_by(Compra.data_hora.desc()).limit(20).all()
    return render_template(
        "compras.html",
        fornecedores=Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.razao_social).all(),
        insumos=Insumo.query.filter_by(ativo=True).order_by(Insumo.nome).all(),
        historico=historico
    )


# ==========================================================
# PRODUÇÃO
# ==========================================================

@app.route("/producao", methods=["GET", "POST"])
@login_required
def producao():
    if request.method == "POST":
        produto = db.get_or_404(Produto, int(request.form["produto_id"]))
        qtd_produzida = decimal_form("qtd_produzida")

        if qtd_produzida <= 0:
            flash("Informe uma quantidade válida.", "danger")
            return redirect(url_for("producao"))

        receita = produto.receita
        if not receita or not receita.itens:
            flash("Este produto ainda não possui uma receita cadastrada.", "danger")
            return redirect(url_for("producao"))

        rendimento = Decimal(receita.rendimento or 1)
        fator = qtd_produzida / rendimento

        consumos = []
        insuficientes = []

        for item in receita.itens:
            necessario = Decimal(item.quantidade) * fator
            consumos.append((item.insumo, necessario))
            if Decimal(item.insumo.qtd_atual or 0) < necessario:
                insuficientes.append(
                    f"{item.insumo.nome}: necessário {necessario:.3f}, disponível {Decimal(item.insumo.qtd_atual or 0):.3f}"
                )

        if insuficientes:
            flash("Saldo insuficiente: " + " | ".join(insuficientes), "danger")
            return redirect(url_for("producao"))

        try:
            p = Producao(
                produto=produto,
                usuario=current_user,
                qtd_produzida=qtd_produzida
            )
            db.session.add(p)
            db.session.flush()

            for insumo, necessario in consumos:
                insumo.qtd_atual = Decimal(insumo.qtd_atual or 0) - necessario
                db.session.add(ItemProducao(
                    producao=p,
                    insumo=insumo,
                    quantidade_usada=necessario
                ))

            produto.qtd_atual = Decimal(produto.qtd_atual or 0) + qtd_produzida
            db.session.commit()
            flash("Produção registrada com sucesso! Estoques atualizados.", "success")
            return redirect(url_for("producao"))
        except Exception:
            db.session.rollback()
            raise

    return render_template(
        "producao.html",
        produtos=Produto.query.filter_by(ativo=True).order_by(Produto.nome).all(),
        historico=Producao.query.order_by(Producao.data_hora.desc()).limit(20).all()
    )


# ==========================================================
# PDV / VENDAS
# ==========================================================

@app.route("/pdv", methods=["GET", "POST"])
@login_required
def pdv():
    if request.method == "POST":
        forma = db.get_or_404(FormaPagamento, int(request.form["forma_pagamento_id"]))
        if not forma.ativo:
            flash("Forma de pagamento indisponível.", "danger")
            return redirect(url_for("pdv"))

        produto_ids = request.form.getlist("produto_id")
        quantidades = request.form.getlist("quantidade")

        itens_validos = []
        total = Decimal("0")
        erros = []

        for produto_id, qtd in zip(produto_ids, quantidades):
            if not produto_id or not qtd.strip():
                continue
            produto = db.session.get(Produto, int(produto_id))
            q = Decimal(qtd.replace(",", "."))
            if not produto or q <= 0:
                continue
            if Decimal(produto.qtd_atual or 0) < q:
                erros.append(f"{produto.nome}: estoque insuficiente")
                continue
            preco = Decimal(produto.preco_venda or 0)
            itens_validos.append((produto, q, preco))
            total += q * preco

        if erros:
            flash(" | ".join(erros), "danger")
            return redirect(url_for("pdv"))

        if not itens_validos:
            flash("Adicione pelo menos um produto à venda.", "danger")
            return redirect(url_for("pdv"))

        try:
            venda = Venda(
                usuario=current_user,
                forma_pagamento=forma,
                valor_total=total
            )
            db.session.add(venda)
            db.session.flush()

            for produto, q, preco in itens_validos:
                produto.qtd_atual = Decimal(produto.qtd_atual or 0) - q
                db.session.add(ItemVenda(
                    venda=venda,
                    produto=produto,
                    quantidade=q,
                    preco_unitario=preco
                ))

            db.session.commit()
            flash("Venda finalizada.", "success")
            return redirect(url_for("comprovante", venda_id=venda.id))
        except Exception:
            db.session.rollback()
            raise

    return render_template(
        "pdv.html",
        produtos=Produto.query.filter_by(ativo=True).order_by(Produto.nome).all(),
        formas=FormaPagamento.query.filter_by(ativo=True).order_by(FormaPagamento.nome).all(),
    )


@app.route("/vendas/<int:venda_id>/comprovante")
@login_required
def comprovante(venda_id):
    venda = db.get_or_404(Venda, venda_id)
    return render_template("comprovante.html", venda=venda)


# ==========================================================
# PERDAS / BAIXAS
# ==========================================================

@app.route("/perdas", methods=["GET", "POST"])
@login_required
def perdas():
    if request.method == "POST":
        tipo = request.form["tipo_item"]
        item_id = int(request.form["item_id"])
        qtd = decimal_form("quantidade")
        motivo = request.form["motivo"]

        if qtd <= 0:
            flash("Informe uma quantidade válida.", "danger")
            return redirect(url_for("perdas"))

        if tipo == "INSUMO":
            item = db.get_or_404(Insumo, item_id)
            saldo = Decimal(item.qtd_atual or 0)
            custo = Decimal(item.custo_medio or 0)
        elif tipo == "PRODUTO":
            item = db.get_or_404(Produto, item_id)
            saldo = Decimal(item.qtd_atual or 0)
            custo = Decimal(item.custo_estimado or 0)
        else:
            abort(400)

        if qtd > saldo:
            flash("A quantidade informada é maior que o saldo em estoque.", "danger")
            return redirect(url_for("perdas"))

        item.qtd_atual = saldo - qtd
        perda = Perda(
            usuario=current_user,
            tipo_item=tipo,
            item_id=item.id,
            nome_item=item.nome,
            quantidade=qtd,
            motivo=motivo,
            custo_unitario=custo,
        )
        db.session.add(perda)
        db.session.commit()
        flash("Baixa registrada com sucesso.", "success")
        return redirect(url_for("perdas"))

    return render_template(
        "perdas.html",
        insumos=Insumo.query.filter_by(ativo=True).order_by(Insumo.nome).all(),
        produtos=Produto.query.filter_by(ativo=True).order_by(Produto.nome).all(),
        historico=Perda.query.order_by(Perda.data_hora.desc()).limit(30).all()
    )


# ==========================================================
# RELATÓRIOS
# ==========================================================

def parse_data(nome, padrao):
    valor = request.args.get(nome)
    if not valor:
        return padrao
    return datetime.strptime(valor, "%Y-%m-%d").date()


@app.route("/relatorios/vendas")
@login_required
def relatorio_vendas():
    admin_required()
    hoje = date.today()
    inicio = parse_data("inicio", hoje.replace(day=1))
    fim = parse_data("fim", hoje)

    vendas = Venda.query.filter(
        func.date(Venda.data_hora) >= inicio,
        func.date(Venda.data_hora) <= fim
    ).order_by(Venda.data_hora.desc()).all()

    faturamento = sum((Decimal(v.valor_total or 0) for v in vendas), Decimal("0"))
    ticket = faturamento / len(vendas) if vendas else Decimal("0")

    produtos = {}
    pagamentos = {}
    for venda in vendas:
        pagamentos[venda.forma_pagamento.nome] = pagamentos.get(venda.forma_pagamento.nome, Decimal("0")) + Decimal(venda.valor_total)
        for item in venda.itens:
            produtos[item.produto.nome] = produtos.get(item.produto.nome, Decimal("0")) + Decimal(item.quantidade)

    ranking = sorted(produtos.items(), key=lambda x: x[1], reverse=True)

    return render_template(
        "relatorio_vendas.html",
        inicio=inicio, fim=fim, vendas=vendas,
        faturamento=faturamento, ticket=ticket,
        ranking=ranking, pagamentos=pagamentos
    )


@app.route("/relatorios/compras")
@login_required
def relatorio_compras():
    admin_required()
    hoje = date.today()
    inicio = parse_data("inicio", hoje.replace(day=1))
    fim = parse_data("fim", hoje)

    compras = Compra.query.filter(
        func.date(Compra.data_hora) >= inicio,
        func.date(Compra.data_hora) <= fim
    ).order_by(Compra.data_hora.desc()).all()

    total = sum((Decimal(c.valor_total or 0) for c in compras), Decimal("0"))
    por_fornecedor = {}
    for c in compras:
        por_fornecedor[c.fornecedor.razao_social] = por_fornecedor.get(c.fornecedor.razao_social, Decimal("0")) + Decimal(c.valor_total)

    ranking = sorted(por_fornecedor.items(), key=lambda x: x[1], reverse=True)

    return render_template(
        "relatorio_compras.html",
        inicio=inicio, fim=fim, compras=compras,
        total=total, ranking=ranking
    )


@app.route("/relatorios/desperdicio")
@login_required
def relatorio_desperdicio():
    admin_required()
    hoje = date.today()
    inicio = parse_data("inicio", hoje.replace(day=1))
    fim = parse_data("fim", hoje)
    motivo = request.args.get("motivo", "")

    query = Perda.query.filter(
        func.date(Perda.data_hora) >= inicio,
        func.date(Perda.data_hora) <= fim
    )
    if motivo:
        query = query.filter_by(motivo=motivo)

    perdas_lista = query.order_by(Perda.data_hora.desc()).all()
    total = sum((p.valor_perda for p in perdas_lista), Decimal("0"))

    por_item = {}
    for p in perdas_lista:
        por_item[p.nome_item] = por_item.get(p.nome_item, Decimal("0")) + p.valor_perda

    ranking = sorted(por_item.items(), key=lambda x: x[1], reverse=True)

    return render_template(
        "relatorio_desperdicio.html",
        inicio=inicio, fim=fim, motivo=motivo,
        perdas=perdas_lista, total=total, ranking=ranking
    )


# ==========================================================
# ERROS
# ==========================================================

@app.errorhandler(403)
def erro_403(e):
    return render_template("erro.html", titulo="Acesso negado", mensagem="Seu perfil não possui permissão para acessar esta página."), 403


@app.errorhandler(404)
def erro_404(e):
    return render_template("erro.html", titulo="Página não encontrada", mensagem="O endereço informado não existe."), 404


# ==========================================================
# SEED INICIAL
# ==========================================================

def seed():
    if not Usuario.query.first():
        admin = Usuario(
            nome="Administrador",
            email="admin@kipao.local",
            perfil="ADMIN",
            ativo=True
        )
        admin.set_senha("admin123")
        db.session.add(admin)

    for nome in ["Dinheiro", "Pix", "Cartão de Débito", "Cartão de Crédito"]:
        if not FormaPagamento.query.filter_by(nome=nome).first():
            db.session.add(FormaPagamento(nome=nome, ativo=True))

    db.session.commit()


def inicializar_banco():
    """Cria as tabelas e os dados iniciais (roda ao subir o app, inclusive no gunicorn)."""
    os.makedirs(app.instance_path, exist_ok=True)
    with app.app_context():
        db.create_all()
        seed()


inicializar_banco()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
