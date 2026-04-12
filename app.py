from flask import Flask, request, redirect, session
import psycopg2
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "cellprotege_secret_key"
app.permanent_session_lifetime = timedelta(minutes=40)

# CON
def conectar():
    return psycopg2.connect(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=6543,
        dbname="postgres",
        user="postgres.gyzqfnxwnnxwzqtzodmu",
        password="senhadobanco",
        sslmode="require"
    )

# LAYOUT
def layout(titulo, conteudo):
    usuario_logado = session.get("usuario")

    topo_direita = ""
    if usuario_logado and titulo != "Login":
        topo_direita = f"""
        <div class="usuario">
            👤 {usuario_logado}
            <a href="/logout"><button class="logout">Sair</button></a>
        </div>
        """

    return f"""
    <html>
    <head>
        <title>{titulo}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background: #6b3fa0;
                color: white;
            }}

            .topo {{
                background: #5a2d91;
                padding: 20px 40px;
                font-size: 28px;
                font-weight: bold;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .logo {{
                color: #00FF00;
            }}

            .usuario {{
                font-size: 14px;
            }}

            .container {{
                width: 900px;
                margin: 40px auto;
                background: rgba(255,255,255,0.05);
                padding: 30px;
                border-radius: 12px;
                backdrop-filter: blur(5px);
            }}

            input {{
                width: 100%;
                padding: 10px;
                margin-bottom: 15px;
                border-radius: 6px;
                border: none;
            }}

            button {{
                background: #facc15;
                color: black;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                transition: 0.2s;
            }}

            button:hover {{
                background: #eab308;
                transform: scale(1.05);
            }}

            .logout {{
                background: #ef4444;
                color: white;
            }}

            .logout:hover {{
                background: #dc2626;
            }}

            a {{
                text-decoration: none;
            }}

            h2, h3 {{
                color: white;
            }}

            hr {{
                border: 1px solid rgba(255,255,255,0.2);
            }}
        </style>
    </head>
    <body>
        <div class="topo">
            <div class="logo">CELL PROTEGE BETA</div>
            {topo_direita}
        </div>

        <div class="container">
            {conteudo}
        </div>
    </body>
    </html>
    """

# LOGIN 
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
            session.permanent = True
            session["usuario"] = usuario[0]
            return redirect("/home")
        else:
            return layout("Login", """
                <h2>Login</h2>
                <p style="color:red;">Email ou senha inválidos</p>
                <form method="POST">
                    Email:<input name="email" required>
                    Senha:<input type="password" name="senha" required>
                    <button type="submit">Entrar</button>
                </form>
            """)

    return layout("Login", """
        <h2>Login</h2>
        <form method="POST">
            Email:<input name="email" required>
            Senha:<input type="password" name="senha" required>
            <button type="submit">Entrar</button>
        </form>
    """)

# HOME
@app.route("/home")
def home():
    if "usuario" not in session:
        return redirect("/")

    return layout("Home", f"""
        <h2>Menu Principal</h2>
        <p>Bem-vindo, {session.get("usuario")}!</p>
        <a href="/clientes"><button>Clientes</button></a>
        <a href="/funcionarios"><button>Funcionários</button></a>
    """)

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/clientes")
def clientes():
    return layout("Clientes", """
        <h2>Clientes</h2>
        <a href="/clientes/cadastrar"><button>Cadastrar</button></a>
        <a href="/clientes/listar"><button>Listar</button></a>
        <br><br>
        <a href="/home"><button>Voltar</button></a>
    """)

#cadastro de funcioanrios
@app.route("/funcionarios/cadastrar", methods=["GET","POST"])
def cadastrar_funcionario():
    if request.method == "POST":
        try:
            with conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO public.funcionarios
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

        except Exception as e:
            return layout("Erro", f"""
                <h2>Erro ao cadastrar</h2>
                <p>CPF ou Email já cadastrados.</p>
                <a href="/funcionarios/cadastrar"><button>Voltar</button></a>
            """)

    return layout("Cadastrar Funcionário", """
        <h2>Cadastrar Funcionário</h2>
        <form method="POST">
            Nome:<input name="nome" required>
            CPF:<input name="cpf" maxlength="14" required>
            Email:<input name="email" required>
            Senha:<input type="password" name="senha" required>
            Cargo:<input name="cargo">
            Telefone:<input name="telefone">
            <button type="submit">Salvar</button>
            <a href="/funcionarios"><button type="button">Voltar</button></a>
        </form>
    """)

# Cadastri cliente
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
                """, (
                    cliente_id,
                    request.form["imei"]
                ))

        return redirect("/clientes/listar")

    return layout("Cadastrar Cliente", """
        <h2>Cadastrar Cliente</h2>
        <form method="POST">
        <h3>Dados Cliente</h3>
        Nome:<input name="nome" required>
        CPF:<input name="cpf" required>
        Email:<input name="email">
        Telefone:<input name="telefone">

        <h3>Endereço</h3>
        Rua:<input name="rua">
        Número:<input name="numero">
        Bairro:<input name="bairro">
        Cidade:<input name="cidade">
        Estado:<input name="estado">
        CEP:<input name="cep">

        <h3>IMEI (15 números)</h3>
        IMEI:<input name="imei" maxlength="15" pattern="[0-9]{15}" required>

        <button type="submit">Salvar</button>
        <a href="/clientes"><button type="button">Voltar</button></a>
        </form>
    """)


# editar cliente

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
                FROM cliente
                WHERE id=%s
            """, (id,))
            cliente = cur.fetchone()

    return layout("Editar Cliente", f"""
        <h2>Editar Cliente</h2>
        <form method="POST">
            Nome:<input name="nome" value="{cliente[0]}" required>
            CPF:<input name="cpf" value="{cliente[1]}" required>
            Email:<input name="email" value="{cliente[2] or ''}">
            Telefone:<input name="telefone" value="{cliente[3] or ''}">
            <button type="submit">Salvar</button>
            <a href="/clientes/listar"><button type="button">Voltar</button></a>
        </form>
    """)

# editar end
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
                FROM enderecos
                WHERE cliente_id=%s
            """, (id,))
            endereco = cur.fetchone()

    if not endereco:
        endereco = ("", "", "", "", "", "")

    return layout("Editar Endereço", f"""
        <h2>Editar Endereço</h2>
        <form method="POST">
            Rua:<input name="rua" value="{endereco[0] or ''}">
            Número:<input name="numero" value="{endereco[1] or ''}">
            Bairro:<input name="bairro" value="{endereco[2] or ''}">
            Cidade:<input name="cidade" value="{endereco[3] or ''}">
            Estado:<input name="estado" value="{endereco[4] or ''}">
            CEP:<input name="cep" value="{endereco[5] or ''}">
            <button type="submit">Salvar</button>
            <a href="/clientes/listar"><button type="button">Voltar</button></a>
        </form>
    """)

# listar cliente
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

    lista = """
        <h2>Lista de Clientes</h2>
        <form method="POST">
            <input name="busca" placeholder="Buscar por CPF ou IMEI">
            <button type="submit">Buscar</button>
        </form>
        <br>
    """

    for c in clientes:
        lista += f"""
            <strong>Nome:</strong> {c[1]}<br>
            <strong>CPF:</strong> {c[2]}<br>
            <strong>Email:</strong> {c[3]}<br>
            <strong>Telefone:</strong> {c[4]}<br>
            <strong>Endereço:</strong> {c[5] or ''}, {c[6] or ''} - {c[7] or ''} - {c[8] or ''}/{c[9] or ''} - CEP {c[10] or ''}<br>
            <strong>IMEIs:</strong> {c[11]}<br><br>

            <a href="/clientes/editar/{c[0]}"><button>Editar Cliente</button></a>
            <a href="/clientes/editar_endereco/{c[0]}"><button>Editar Endereço</button></a>
            <a href="/clientes/excluir/{c[0]}"><button>Excluir</button></a>
            <a href="/clientes/adicionar_imei/{c[0]}"><button>Adicionar IMEI</button></a>
            <hr>
        """

    lista += '<a href="/clientes"><button>Voltar</button></a>'
    return layout("Lista Clientes", lista)

# ADICIONAR IMEI
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

    return layout("Adicionar IMEI", """
        <h2>Adicionar IMEI</h2>
        <form method="POST">
            IMEI:<input name="imei" maxlength="15" pattern="[0-9]{15}" required>
            <button type="submit">Salvar</button>
        </form>
    """)

# Excluir Cliente
@app.route("/clientes/excluir/<int:id>")
def excluir_cliente(id):
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cliente WHERE id=%s",(id,))
    return redirect("/clientes/listar")

# Funcionarios
@app.route("/funcionarios")
def funcionarios():
    return layout("Funcionários", """
        <h2>Funcionários</h2>
        <a href="/funcionarios/cadastrar"><button>Cadastrar</button></a>
        <a href="/funcionarios/listar"><button>Listar</button></a>
        <br><br>
        <a href="/home"><button>Voltar</button></a>
    """)

#Listar funcionario

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

    lista = """
        <h2>Lista de Funcionários</h2>
        <style>
            .card-funcionario {
                background: rgba(255,255,255,0.08);
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 12px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.2);
                transition: 0.2s;
            }

            .card-funcionario:hover {
                transform: scale(1.02);
            }

            .nome-topo {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 18px;
                font-weight: bold;
            }

            .btn-editar {
                background: #3b82f6;
                color: white;
                padding: 5px 12px;
                font-size: 12px;
                border-radius: 6px;
                border: none;
                cursor: pointer;
            }

            .btn-editar:hover {
                background: #2563eb;
            }
        </style>
    """

    if not dados:
        lista += "<p>Nenhum funcionário cadastrado.</p>"

    for d in dados:
        lista += f"""
            <div class="card-funcionario">
                <div class="nome-topo">
                    <span>{d[1]}</span>
                    <a href="/funcionarios/editar/{d[0]}">
                        <button class="btn-editar">Editar</button>
                    </a>
                </div>
                <br>
                <strong>CPF:</strong> {d[2]}<br>
                <strong>Cargo:</strong> {d[3] if d[3] else '-'}<br>
                <strong>Telefone:</strong> {d[4] if d[4] else '-'}
            </div>
        """

    lista += '<a href="/funcionarios"><button>Voltar</button></a>'
    return layout("Lista Funcionários", lista)

#Editar funcionario

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
                FROM funcionarios
                WHERE id_funcionario=%s
            """, (id,))
            funcionario = cur.fetchone()

    return layout("Editar Funcionário", f"""
        <h2>Editar Funcionário</h2>
        <form method="POST">
            Nome:<input name="nome" value="{funcionario[0]}" required>
            CPF:<input name="cpf" value="{funcionario[1]}" required>
            Email:<input name="email" value="{funcionario[2]}">
            Cargo:<input name="cargo" value="{funcionario[3] or ''}">
            Telefone:<input name="telefone" value="{funcionario[4] or ''}">

            <button type="submit">Salvar Alterações</button>
            <a href="/funcionarios/listar">
                <button type="button">Voltar</button>
            </a>
        </form>

        <br><hr><br>

        <h3>Segurança</h3>
        <a href="/funcionarios/alterar_senha/{id}">
            <button style="background:#10b981; color:white;">
                Alterar Senha
            </button>
        </a>
    """)

#Senha

@app.route("/funcionarios/alterar_senha/<int:id>", methods=["GET","POST"])
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

    return layout("Alterar Senha", f"""
        <h2>Alterar Senha</h2>
        <form method="POST">
            Nova Senha:
            <input type="password" name="senha" required>
            <button type="submit">Salvar</button>
            <a href="/funcionarios/editar/{id}">
                <button type="button">Cancelar</button>
            </a>
        </form>
    """)
# Flask 
if __name__ == "__main__":
    app.run()