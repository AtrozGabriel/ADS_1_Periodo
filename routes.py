from flask import request, redirect, session, render_template, abort
from functools import wraps
from models import conectar
import uuid
from supabase import create_client
import os

SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
BUCKET = "documentos-clientes"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def login_required(perfis=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "usuario" not in session:
                return redirect("/login")

            if perfis and session.get("perfil") not in perfis:
                return abort(403)

            return f(*args, **kwargs)
        return wrapper
    return decorator

def upload_arquivo(arquivo, cliente_id, tipo_solicitacao, tipo_arquivo):
    extensao = arquivo.filename.rsplit(".", 1)[-1].lower()
    nome_unico = f"{tipo_arquivo}_{uuid.uuid4().hex}.{extensao}"
    caminho = f"cliente_{cliente_id}/{tipo_solicitacao}/{nome_unico}"

    supabase.storage.from_(BUCKET).upload( # type: ignore
        path=caminho,
        file=arquivo.read(),
        file_options={
            "content-type": arquivo.mimetype
        }
    )

    return caminho


def _perfil_do_cargo(cargo):
    cargo = (cargo or "").strip().lower()

    if cargo == "admin":
        return "admin"

    if cargo == "atendente":
        return "atendente"

    return None


def init_routes(app):

    @app.route("/")
    def index():

        if "usuario" in session:

            if session.get("perfil") in [
                "admin",
                "atendente"
            ]:
                return redirect("/home")

            if session.get("perfil") == "cliente":
                return redirect("/acesso-cliente")

        return render_template("tela_inicial.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            senha = request.form.get("senha")

            with conectar() as conn:
                with conn.cursor() as cur:

                    cur.execute("""
                        SELECT id_funcionario, nome, cargo
                        FROM funcionarios
                        WHERE email = %s
                          AND senha = %s
                          AND status = true
                    """, (email, senha))

                    funcionario = cur.fetchone()

                    if funcionario:
                        perfil = _perfil_do_cargo(funcionario[2])

                        if perfil is None:
                            return render_template("login.html", erro=True)

                        session.permanent = True
                        session["usuario_id"] = funcionario[0]
                        session["usuario"] = funcionario[1]
                        session["perfil"] = perfil
                        session["cargo"] = funcionario[2]

                        return redirect("/home")

                    cur.execute("""
                        SELECT id, nome
                        FROM cliente
                        WHERE email = %s
                        AND senha = %s
                        AND status = true
                    """, (email, senha))

                    cliente = cur.fetchone()

                    if cliente:
                        session.permanent = True
                        session["usuario_id"] = cliente[0]
                        session["usuario"] = cliente[1]
                        session["perfil"] = "cliente"

                        return redirect("/acesso-cliente")

            return render_template("login.html", erro=True)

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect("/")

    @app.route("/home")
    @login_required(["admin", "atendente"])
    def home():
        return render_template(
            "home.html",
            usuario=session.get("usuario"),
            perfil=session.get("perfil"),
            cargo=session.get("cargo")
        )

    @app.route("/admin")
    @login_required(["admin"])
    def admin():
        return render_template(
            "admin.html",
            usuario=session.get("usuario")
        )

    @app.route("/acesso-cliente")
    @login_required(["cliente"])
    def acesso_cliente():
        with conectar() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT c.nome, c.email, c.telefone
                    FROM cliente c
                    WHERE c.id = %s
                """, (session["usuario_id"],))
                cliente = cur.fetchone()

                cur.execute("""
                    SELECT numero
                    FROM imei
                    WHERE cliente_id = %s
                """, (session["usuario_id"],))
                imeis = cur.fetchall()

        return render_template(
            "acesso_cliente.html",
            cliente=cliente,
            imeis=imeis
        )

    @app.route("/clientes")
    @login_required(["admin", "atendente"])
    def clientes():
        return render_template("clientes.html")

    @app.route("/clientes/cadastrar", methods=["GET", "POST"])
    @login_required(["admin", "atendente"])
    def cadastrar_cliente():
        if request.method == "POST":
            with conectar() as conn:
                with conn.cursor() as cur:

                    cur.execute("""
                        INSERT INTO cliente
                        (nome, cpf, email, telefone, senha)
                        VALUES (%s,%s,%s,%s,%s)
                        RETURNING id
                    """, (
                        request.form["nome"],
                        request.form["cpf"],
                        request.form["email"],
                        request.form["telefone"],
                        request.form["senha"]
                    ))

                    cliente_id = cur.fetchone()[0]

                    cur.execute("""
                        INSERT INTO enderecos
                        (cliente_id, rua, numero, bairro, cidade, estado, cep)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        cliente_id,
                        request.form["rua"],
                        request.form["numero"],
                        request.form["bairro"],
                        request.form["cidade"],
                        request.form["estado"],
                        request.form["cep"]
                    ))

                    cur.execute("""
                        INSERT INTO imei
                        (cliente_id, numero)
                        VALUES (%s,%s)
                    """, (
                        cliente_id,
                        request.form["imei"]
                    ))

            return redirect("/clientes/listar")

        return render_template("clientes_cadastrar.html")

    @app.route("/clientes/listar", methods=["GET", "POST"])
    @login_required(["admin", "atendente"])
    def listar_clientes():
        condicoes = []
        parametros = []

        if session.get("perfil") == "atendente":
            condicoes.append("c.status = true")

        if request.method == "POST":
            busca = request.form["busca"]
            condicoes.append("(c.cpf = %s OR i.numero = %s)")
            parametros.extend([busca, busca])

        where_sql = ""
        if condicoes:
            where_sql = "WHERE " + " AND ".join(condicoes)

        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT
                        c.id,
                        c.nome,
                        c.cpf,
                        c.email,
                        c.telefone,
                        e.rua,
                        e.numero,
                        e.bairro,
                        e.cidade,
                        e.estado,
                        e.cep,
                        COALESCE(string_agg(i.numero, ', '), '—'),
                        c.status
                    FROM cliente c
                    LEFT JOIN enderecos e ON c.id = e.cliente_id
                    LEFT JOIN imei i ON c.id = i.cliente_id
                    {where_sql}
                    GROUP BY
                        c.id, c.nome, c.cpf, c.email, c.telefone,
                        e.rua, e.numero, e.bairro, e.cidade, e.estado, e.cep,
                        c.status
                    ORDER BY c.nome
                """, tuple(parametros))

                clientes = cur.fetchall()

        return render_template("clientes_listar.html", clientes=clientes)
    
    @app.route("/clientes/alternar_status/<int:id>", methods=["POST"])
    @login_required(["admin"])
    def alternar_status_cliente(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE cliente
                    SET status = NOT status
                    WHERE id = %s
                """, (id,))

        return redirect("/clientes/listar")

    @app.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
    @login_required(["admin", "atendente"])
    def editar_cliente(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                if request.method == "POST":
                    cur.execute("""
                        UPDATE cliente
                        SET nome=%s, cpf=%s, email=%s, telefone=%s
                        WHERE id=%s
                    """, (
                        request.form["nome"],
                        request.form["cpf"],
                        request.form["email"],
                        request.form["telefone"],
                        id
                    ))
                    return redirect("/clientes/listar")

                cur.execute("""
                    SELECT nome, cpf, email, telefone
                    FROM cliente
                    WHERE id=%s
                """, (id,))
                cliente = cur.fetchone()

        return render_template("clientes_editar.html", cliente=cliente, id=id)

    @app.route("/clientes/editar_endereco/<int:id>", methods=["GET", "POST"])
    @login_required(["admin", "atendente"])
    def editar_endereco(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                if request.method == "POST":
                    cur.execute("""
                        UPDATE enderecos
                        SET rua=%s, numero=%s, bairro=%s,
                            cidade=%s, estado=%s, cep=%s
                        WHERE cliente_id=%s
                    """, (
                        request.form["rua"],
                        request.form["numero"],
                        request.form["bairro"],
                        request.form["cidade"],
                        request.form["estado"],
                        request.form["cep"],
                        id
                    ))
                    return redirect("/clientes/listar")

                cur.execute("""
                    SELECT rua, numero, bairro, cidade, estado, cep
                    FROM enderecos
                    WHERE cliente_id=%s
                """, (id,))
                endereco = cur.fetchone()

        return render_template("endereco_editar.html", endereco=endereco, id=id)

    @app.route("/clientes/adicionar_imei/<int:id>", methods=["GET", "POST"])
    @login_required(["admin", "atendente"])
    def adicionar_imei(id):
        if request.method == "POST":
            with conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO imei (cliente_id, numero)
                        VALUES (%s,%s)
                    """, (id, request.form["imei"]))

            return redirect("/clientes/listar")

        return render_template("imei_add.html", id=id)

    @app.route("/clientes/excluir/<int:id>")
    @login_required(["admin", "atendente"])
    def excluir_cliente(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM cliente
                    WHERE id=%s
                """, (id,))

        return redirect("/clientes/listar")

    @app.route("/funcionarios") 
    @login_required(["admin"])
    def funcionarios():
        return render_template("funcionarios.html")

    @app.route("/funcionarios/cadastrar", methods=["GET", "POST"])
    @login_required(["admin"])
    def cadastrar_funcionario():
        if request.method == "POST":
            with conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO funcionarios
                        (nome, cpf, email, senha, cargo, telefone)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (
                        request.form["nome"],
                        request.form["cpf"],
                        request.form["email"],
                        request.form["senha"],
                        request.form["cargo"],
                        request.form["telefone"]
                    ))

            return redirect("/funcionarios/listar")

        return render_template("funcionarios_cadastrar.html")

    @app.route("/funcionarios/listar")
    @login_required(["admin"])
    def listar_funcionarios():
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id_funcionario, nome, cpf, cargo, telefone
                    FROM funcionarios
                    WHERE status = true
                    ORDER BY nome
                """)
                dados = cur.fetchall()

        return render_template("funcionarios_listar.html", dados=dados)

    @app.route("/funcionarios/editar/<int:id>", methods=["GET", "POST"])
    @login_required(["admin"])
    def editar_funcionario(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                if request.method == "POST":
                    cur.execute("""
                        UPDATE funcionarios
                        SET nome=%s, cpf=%s, email=%s,
                            cargo=%s, telefone=%s
                        WHERE id_funcionario=%s
                    """, (
                        request.form["nome"],
                        request.form["cpf"],
                        request.form["email"],
                        request.form["cargo"],
                        request.form["telefone"],
                        id
                    ))
                    return redirect("/funcionarios/listar")

                cur.execute("""
                    SELECT nome, cpf, email, cargo, telefone
                    FROM funcionarios
                    WHERE id_funcionario=%s
                """, (id,))
                funcionario = cur.fetchone()

        return render_template("funcionarios_editar.html", f=funcionario, id=id)

    @app.route("/funcionarios/alterar_senha/<int:id>", methods=["GET", "POST"])
    @login_required(["admin"])
    def alterar_senha(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                if request.method == "POST":
                    nova_senha = request.form["senha"]

                    cur.execute("""
                        UPDATE funcionarios
                        SET senha=%s
                        WHERE id_funcionario=%s
                    """, (nova_senha, id))

                    return redirect(f"/funcionarios/editar/{id}")

        return render_template("alterar_senha.html", id=id)

    @app.route("/servicos")
    def servicos():
        return render_template("servicos.html")
    
    @app.route("/abrir-chamado")
    @login_required(["cliente"])
    def abrir_chamado():
        return render_template("abrir_chamado.html")


    @app.route("/abrir-chamado/roubo-furto", methods=["GET", "POST"])
    @login_required(["cliente"])
    def roubo_furto():
        if request.method == "POST":
            boletim = request.files.get("boletim")
            nota_fiscal = request.files.get("nota_fiscal")
            descricao = request.form.get("descricao", "")

            if not boletim or not nota_fiscal:
                return render_template(
                    "chamado_roubo_furto.html",
                    erro="Envie o boletim de ocorrência e a nota fiscal."
                )

            with conectar() as conn:
                with conn.cursor() as cur:

                    cur.execute("""
                        INSERT INTO solicitacoes_documentos
                        (cliente_id, tipo_solicitacao, descricao, status_analise)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        session["usuario_id"],
                        "roubo_furto",
                        descricao,
                        "em_analise"
                    ))

                    solicitacao_id = cur.fetchone()[0]

                    caminho_boletim = upload_arquivo(
                        boletim,
                        session["usuario_id"],
                        "roubo_furto",
                        "boletim_ocorrencia"
                    )

                    cur.execute("""
                        INSERT INTO solicitacoes_arquivos
                        (solicitacao_id, tipo_arquivo, bucket_nome, caminho_arquivo, nome_arquivo_original, mime_type, status_arquivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        solicitacao_id,
                        "boletim_ocorrencia",
                        BUCKET,
                        caminho_boletim,
                        boletim.filename,
                        boletim.mimetype,
                        "pendente"
                    ))

                    caminho_nf = upload_arquivo(
                        nota_fiscal,
                        session["usuario_id"],
                        "roubo_furto",
                        "nota_fiscal"
                    )

                    cur.execute("""
                        INSERT INTO solicitacoes_arquivos
                        (solicitacao_id, tipo_arquivo, bucket_nome, caminho_arquivo, nome_arquivo_original, mime_type, status_arquivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        solicitacao_id,
                        "nota_fiscal",
                        BUCKET,
                        caminho_nf,
                        nota_fiscal.filename,
                        nota_fiscal.mimetype,
                        "pendente"
                    ))

            return redirect("/acesso-cliente")

        return render_template("chamado_roubo_furto.html")


    @app.route("/abrir-chamado/danos-materiais", methods=["GET", "POST"])
    @login_required(["cliente"])
    def danos_materiais():
        if request.method == "POST":
            foto_celular = request.files.get("foto_celular")
            nota_fiscal = request.files.get("nota_fiscal")
            descricao = request.form.get("descricao", "")

            if not foto_celular or not nota_fiscal:
                return render_template(
                    "chamado_danos_materiais.html",
                    erro="Envie a foto do celular e a nota fiscal."
                )

            with conectar() as conn:
                with conn.cursor() as cur:

                    cur.execute("""
                        INSERT INTO solicitacoes_documentos
                        (cliente_id, tipo_solicitacao, descricao, status_analise)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        session["usuario_id"],
                        "danos_materiais",
                        descricao,
                        "em_analise"
                    ))

                    solicitacao_id = cur.fetchone()[0]

                    caminho_foto = upload_arquivo(
                        foto_celular,
                        session["usuario_id"],
                        "danos_materiais",
                        "foto_celular"
                    )

                    cur.execute("""
                        INSERT INTO solicitacoes_arquivos
                        (solicitacao_id, tipo_arquivo, bucket_nome, caminho_arquivo, nome_arquivo_original, mime_type, status_arquivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        solicitacao_id,
                        "foto_celular",
                        BUCKET,
                        caminho_foto,
                        foto_celular.filename,
                        foto_celular.mimetype,
                        "pendente"
                    ))

                    caminho_nf = upload_arquivo(
                        nota_fiscal,
                        session["usuario_id"],
                        "danos_materiais",
                        "nota_fiscal"
                    )

                    cur.execute("""
                        INSERT INTO solicitacoes_arquivos
                        (solicitacao_id, tipo_arquivo, bucket_nome, caminho_arquivo, nome_arquivo_original, mime_type, status_arquivo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        solicitacao_id,
                        "nota_fiscal",
                        BUCKET,
                        caminho_nf,
                        nota_fiscal.filename,
                        nota_fiscal.mimetype,
                        "pendente"
                    ))

            return redirect("/acesso-cliente")

        return render_template("chamado_danos_materiais.html")
    
    @app.route("/acompanhar")
    @login_required(["cliente"])
    def acompanhar():

        with conectar() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT
                        id,
                        tipo_solicitacao,
                        status_analise,
                        criado_em
                    FROM solicitacoes_documentos
                    WHERE cliente_id = %s
                    ORDER BY criado_em DESC
                """, (
                    session["usuario_id"],
                ))

                chamados = cur.fetchall()

        return render_template(
            "acompanhar.html",
            chamados=chamados
        )
    
    @app.route("/cancelar-chamado/<int:id>", methods=["POST"])
    @login_required(["cliente"])
    def cancelar_chamado(id):

        with conectar() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    SELECT caminho_arquivo
                    FROM solicitacoes_arquivos
                    WHERE solicitacao_id = %s
                """, (id,))

                arquivos = cur.fetchall()

                for arquivo in arquivos:

                    supabase.storage.from_(BUCKET).remove([
                        arquivo[0]
                    ])

                cur.execute("""
                    DELETE FROM solicitacoes_documentos
                    WHERE id = %s
                    AND cliente_id = %s
                """, (
                    id,
                    session["usuario_id"]
                ))

        return redirect("/acompanhar")
    
    @app.route("/chamados")
    @login_required(["admin"])
    def chamados():
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        sd.id,
                        c.nome,
                        sd.tipo_solicitacao,
                        sd.descricao,
                        sd.status_analise,
                        sd.criado_em
                    FROM solicitacoes_documentos sd
                    JOIN cliente c ON c.id = sd.cliente_id
                    ORDER BY sd.criado_em DESC
                """)
                chamados = cur.fetchall()

        return render_template("chamados.html", chamados=chamados)


    @app.route("/chamados/<int:id>/aprovar", methods=["POST"])
    @login_required(["admin"])
    def aprovar_chamado(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE solicitacoes_documentos
                    SET status_analise = 'aprovado'
                    WHERE id = %s
                """, (id,))

        return redirect("/chamados")


    @app.route("/chamados/<int:id>/reprovar", methods=["POST"])
    @login_required(["admin"])
    def reprovar_chamado(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE solicitacoes_documentos
                    SET status_analise = 'reprovado'
                    WHERE id = %s
                """, (id,))

        return redirect("/chamados")