from flask import request, redirect, session, render_template
from models import conectar

def init_routes(app):

    @app.route("/", methods=["GET","POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            senha = request.form.get("senha")

            with conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT nome
                        FROM funcionarios
                        WHERE email = %s AND senha = %s AND status = true
                    """, (email, senha))
                    usuario = cur.fetchone()

            if usuario:
                session["usuario"] = usuario[0]
                return redirect("/home")

            return render_template("login.html", erro=True)

        return render_template("login.html")

    @app.route("/home")
    def home():
        if "usuario" not in session:
            return redirect("/")
        return render_template("home.html", usuario=session["usuario"])

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect("/")

    @app.route("/clientes")
    def clientes():
        return render_template("clientes.html")

    @app.route("/clientes/cadastrar", methods=["GET","POST"])
    def cadastrar_cliente():
        if request.method == "POST":
            with conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO cliente (nome, cpf, email, telefone)
                        VALUES (%s,%s,%s,%s)
                        RETURNING id
                    """, (
                        request.form["nome"],
                        request.form["cpf"],
                        request.form["email"],
                        request.form["telefone"]
                    ))
                    cliente_id = cur.fetchone()[0]

                    cur.execute("""
                        INSERT INTO enderecos (cliente_id, rua, numero, bairro, cidade, estado, cep)
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
                        INSERT INTO imei (cliente_id, numero)
                        VALUES (%s,%s)
                    """, (cliente_id, request.form["imei"]))

            return redirect("/clientes/listar")

        return render_template("clientes_cadastrar.html")

    @app.route("/clientes/listar", methods=["GET","POST"])
    def listar_clientes():
        filtro = ""
        parametros = ()

        if request.method == "POST":
            busca = request.form["busca"]
            filtro = "WHERE c.cpf = %s OR i.numero = %s"
            parametros = (busca, busca)

        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT c.id, c.nome, c.cpf, c.email, c.telefone,
                           e.rua, e.numero, e.bairro, e.cidade, e.estado, e.cep,
                           COALESCE(string_agg(i.numero, ', '), '—')
                    FROM cliente c
                    LEFT JOIN enderecos e ON c.id = e.cliente_id
                    LEFT JOIN imei i ON c.id = i.cliente_id
                    {filtro}
                    GROUP BY c.id, c.nome, c.cpf, c.email, c.telefone,
                             e.rua, e.numero, e.bairro, e.cidade, e.estado, e.cep
                    ORDER BY c.nome
                """, parametros)
                clientes = cur.fetchall()

        return render_template("clientes_listar.html", clientes=clientes)

    @app.route("/clientes/editar/<int:id>", methods=["GET","POST"])
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
                    FROM cliente WHERE id=%s
                """, (id,))
                cliente = cur.fetchone()

        return render_template("clientes_editar.html", cliente=cliente, id=id)

    @app.route("/clientes/editar_endereco/<int:id>", methods=["GET","POST"])
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
                    FROM enderecos WHERE cliente_id=%s
                """, (id,))
                endereco = cur.fetchone()

        return render_template("endereco_editar.html", endereco=endereco, id=id)

    @app.route("/clientes/adicionar_imei/<int:id>", methods=["GET","POST"])
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
    def excluir_cliente(id):
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cliente WHERE id=%s",(id,))
        return redirect("/clientes/listar")

    # FUNCIONÁRIOS
    @app.route("/funcionarios")
    def funcionarios():
        return render_template("funcionarios.html")

    @app.route("/funcionarios/cadastrar", methods=["GET","POST"])
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
    def listar_funcionarios():
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id_funcionario, nome, cpf, cargo, telefone
                    FROM funcionarios
                    ORDER BY nome
                """)
                dados = cur.fetchall()

        return render_template("funcionarios_listar.html", dados=dados)

    @app.route("/funcionarios/editar/<int:id>", methods=["GET","POST"])
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
                    FROM funcionarios WHERE id_funcionario=%s
                """, (id,))
                funcionario = cur.fetchone()

        return render_template("funcionarios_editar.html", f=funcionario, id=id)

    @app.route("/funcionarios/alterar_senha/<int:id>", methods=["GET","POST"])
    def alterar_senha(id):
        if request.method == "POST":
            with conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE funcionarios
                        SET senha=%s WHERE id_funcionario=%s
                    """, (request.form["senha"], id))
            return redirect(f"/funcionarios/editar/{id}")

        return render_template("alterar_senha.html", id=id)