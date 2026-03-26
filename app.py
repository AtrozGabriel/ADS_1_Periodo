from flask import Flask, request, redirect
import psycopg2

app = Flask(__name__)

def conectar():
    return psycopg2.connect(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=6543,
        dbname="postgres",
        user="postgres.gyzqfnxwnnxwzqtzodmu",
        password="senhadobanco",
        sslmode="require"
    )

def layout(titulo, conteudo):
    return f"""
    <html>
    <head>
        <title>{titulo}</title>
        <style>
            body {{
                font-family: Arial;
                background: #f4f6f9;
                margin: 0;
            }}
            .topo {{
                background: #111827;
                color: white;
                padding: 20px;
                text-align: center;
                font-size: 24px;
                font-weight: bold;
            }}
            .container {{
                width: 850px;
                margin: 30px auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 15px rgba(0,0,0,0.08);
            }}
            input {{
                width: 100%;
                padding: 8px;
                margin-bottom: 12px;
            }}
            button {{
                background: #2563eb;
                color: white;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                margin-right: 5px;
            }}
            button:hover {{
                background: #1d4ed8;
            }}
            a {{
                text-decoration: none;
            }}
            h3 {{
                margin-top: 25px;
            }}
        </style>
    </head>
    <body>
        <div class="topo">CELL PROTEGE BETA</div>
        <div class="container">
            {conteudo}
        </div>
    </body>
    </html>
    """


@app.route("/")
def home():
    conteudo = """
    <h2>Menu Principal</h2>
    <a href="/clientes"><button>Clientes</button></a>
    <a href="/funcionarios"><button>Funcionários</button></a>
    """
    return layout("Home", conteudo)

# CLIENTES

@app.route("/clientes")
def clientes():
    conteudo = """
    <h2>Clientes</h2>
    <a href="/clientes/cadastrar"><button>Cadastrar</button></a>
    <a href="/clientes/listar"><button>Listar</button></a>
    <br><br>
    <a href="/"><button>Voltar</button></a>
    """
    return layout("Clientes", conteudo)

# CADASTRAR CLIENTE

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
                    INSERT INTO imei (cliente_id, numero)
                    VALUES (%s,%s)
                """, (
                    cliente_id,
                    request.form["imei"]
                ))

        return redirect("/clientes/listar")

    conteudo = """
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
    </form>
    """

    return layout("Cadastrar Cliente", conteudo)

# LISTAR + BUSCAR CLIENTES
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

            if filtro:
                cur.execute(f"""
                    SELECT DISTINCT c.id, c.nome, c.cpf, c.email, c.telefone,
                           e.rua, e.numero, e.bairro, e.cidade, e.estado, e.cep
                    FROM cliente c
                    LEFT JOIN enderecos e ON c.id = e.cliente_id
                    LEFT JOIN imei i ON c.id = i.cliente_id
                    {filtro}
                """, parametros)
            else:
                cur.execute("""
                    SELECT c.id, c.nome, c.cpf, c.email, c.telefone,
                           e.rua, e.numero, e.bairro, e.cidade, e.estado, e.cep
                    FROM cliente c
                    LEFT JOIN enderecos e ON c.id = e.cliente_id
                """)

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

        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT numero FROM imei WHERE cliente_id=%s",(c[0],))
                imeis = cur.fetchall()

        lista_imeis = ", ".join([i[0] for i in imeis]) if imeis else "—"

        lista += f"""
        <strong>Nome:</strong> {c[1]}<br>
        <strong>CPF:</strong> {c[2]}<br>
        <strong>Email:</strong> {c[3]}<br>
        <strong>Telefone:</strong> {c[4]}<br>
        <strong>Endereço:</strong> {c[5]}, {c[6]} - {c[7]} - {c[8]}/{c[9]} - CEP {c[10]}<br>
        <strong>IMEIs:</strong> {lista_imeis}<br><br>

        <a href="/clientes/editar/{c[0]}"><button>Editar</button></a>
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

    conteudo = """
    <h2>Adicionar IMEI</h2>
    <form method="POST">
    IMEI:<input name="imei" maxlength="15" pattern="[0-9]{15}" required>
    <button type="submit">Salvar</button>
    </form>
    """

    return layout("Adicionar IMEI", conteudo)

# EDITAR CLIENTE + ENDEREÇO
@app.route("/clientes/editar/<int:id>", methods=["GET","POST"])
def editar_cliente(id):

    if request.method == "POST":
        with conectar() as conn:
            with conn.cursor() as cur:

                cur.execute("""
                    UPDATE cliente
                    SET nome=%s, email=%s, telefone=%s
                    WHERE id=%s
                """, (
                    request.form["nome"],
                    request.form["email"],
                    request.form["telefone"],
                    id
                ))

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

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.nome, c.email, c.telefone,
                       e.rua, e.numero, e.bairro, e.cidade, e.estado, e.cep
                FROM cliente c
                LEFT JOIN enderecos e ON c.id = e.cliente_id
                WHERE c.id=%s
            """,(id,))
            c = cur.fetchone()

    conteudo = f"""
    <h2>Editar Cliente</h2>
    <form method="POST">
    Nome:<input name="nome" value="{c[0]}">
    Email:<input name="email" value="{c[1]}">
    Telefone:<input name="telefone" value="{c[2]}">

    <h3>Endereço</h3>
    Rua:<input name="rua" value="{c[3]}">
    Número:<input name="numero" value="{c[4]}">
    Bairro:<input name="bairro" value="{c[5]}">
    Cidade:<input name="cidade" value="{c[6]}">
    Estado:<input name="estado" value="{c[7]}">
    CEP:<input name="cep" value="{c[8]}">

    <button type="submit">Atualizar</button>
    </form>
    """

    return layout("Editar Cliente", conteudo)

# EXCLUIR CLIENTE
@app.route("/clientes/excluir/<int:id>")
def excluir_cliente(id):

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cliente WHERE id=%s",(id,))

    return redirect("/clientes/listar")

# FUNCIONÁRIOS
@app.route("/funcionarios")
def funcionarios():
    conteudo = """
    <h2>Funcionários</h2>
    <a href="/funcionarios/cadastrar"><button>Cadastrar</button></a>
    <a href="/funcionarios/listar"><button>Listar</button></a>
    <br><br>
    <a href="/"><button>Voltar</button></a>
    """
    return layout("Funcionários", conteudo)

@app.route("/funcionarios/cadastrar", methods=["GET","POST"])
def cadastrar_funcionario():

    if request.method == "POST":
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO funcionarios (nome, cpf, cargo, email, senha)
                    VALUES (%s,%s,%s,%s,%s)
                """, (
                    request.form["nome"],
                    request.form["cpf"],
                    request.form["cargo"],
                    request.form["email"],
                    request.form["senha"]
                ))

        return redirect("/funcionarios/listar")

    conteudo = """
    <h2>Cadastrar Funcionário</h2>
    <form method="POST">
    Nome:<input name="nome">
    CPF:<input name="cpf">
    Cargo:<input name="cargo">
    Email:<input name="email">
    Senha:<input type="password" name="senha" required>
    <button type="submit">Salvar</button>
    </form>
    """

    return layout("Cadastrar Funcionário", conteudo)

@app.route("/funcionarios/listar")
def listar_funcionarios():

    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_funcionario, nome, cpf, cargo, telefone, status
                FROM funcionarios
            """)
            dados = cur.fetchall()

    lista = "<h2>Lista Funcionários</h2>"

    if not dados:
        lista += "<p>Nenhum funcionário cadastrado.</p>"

    for d in dados:
        lista += f"""
        <strong>ID:</strong> {d[0]} |
        <strong>Nome:</strong> {d[1]} |
        <strong>CPF:</strong> {d[2]} |
        <strong>Cargo:</strong> {d[3] if d[3] else '-'} |
        <strong>Telefone:</strong> {d[4] if d[4] else '-'} |
        <strong>Status:</strong> {"Ativo" if d[5] else "Inativo"}
        <br><br>
        """

    lista += '<a href="/funcionarios"><button>Voltar</button></a>'

    return layout("Lista Funcionários", lista)

if __name__ == "__main__":
    app.run(debug=True)