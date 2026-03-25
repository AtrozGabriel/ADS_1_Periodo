from flask import Flask, request, redirect
import psycopg

app = Flask(__name__)

def conectar():
    return psycopg.connect(
        host="localhost",
        port=5432,
        dbname="banco",
        user="postgres",
        password="senha123"
    )

# ================= MENU =================
@app.route("/")
def menu():
    return """
    <h1>Sistema</h1>
    <a href="/clientes"><button>Clientes</button></a>
    <a href="/funcionarios"><button>Funcionários</button></a>
    """

# ================= CLIENTES =================
@app.route("/clientes")
def clientes_menu():
    return """
    <h1>Clientes</h1>
    <a href="/"><button>Voltar</button></a>
    <a href="/clientes/cadastrar"><button>Cadastrar</button></a>
    <a href="/clientes/listar"><button>Listar</button></a>
    <a href="/clientes/pesquisar"><button>Pesquisar</button></a>
    """

# -------- CADASTRAR CLIENTE --------
@app.route("/clientes/cadastrar", methods=["GET", "POST"])
def cadastrar_cliente():
    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        email = request.form["email"]
        telefone = request.form["telefone"]

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO clientes (nome, cpf, email, telefone)
            VALUES (%s, %s, %s, %s)
        """, (nome, cpf, email, telefone))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/clientes/listar")

    return """
    <h2>Cadastrar Cliente</h2>
    <form method="POST">
        Nome: <input name="nome" required><br><br>
        CPF: <input name="cpf" required><br><br>
        Email: <input name="email"><br><br>
        Telefone: <input name="telefone"><br><br>
        <button type="submit">Salvar</button>
    </form>
    <a href="/clientes"><button>Voltar</button></a>
    """

# -------- LISTAR CLIENTES (COM IMEIs) --------
@app.route("/clientes/listar")
def listar_clientes():

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            c.id,
            c.nome,
            c.cpf,
            c.email,
            c.telefone,
            STRING_AGG(i.imei, ', ') AS imeis
        FROM clientes c
        LEFT JOIN imeis i ON c.id = i.cliente_id
        GROUP BY c.id
        ORDER BY c.id
    """)

    clientes = cur.fetchall()

    cur.close()
    conn.close()

    html = "<h2>Lista de Clientes</h2>"
    html += "<a href='/clientes'><button>Voltar</button></a><hr>"

    for c in clientes:
        imeis = c[5] if c[5] else "Nenhum IMEI cadastrado"

        html += f"""
        <p>
        ID: {c[0]} <br>
        Nome: {c[1]} <br>
        CPF: {c[2]} <br>
        Email: {c[3]} <br>
        Telefone: {c[4]} <br>
        IMEIs: {imeis} <br><br>

        <a href='/clientes/editar/{c[0]}'><button>Editar</button></a>
        <a href='/clientes/excluir/{c[0]}'><button>Excluir</button></a>
        </p>
        <hr>
        """

    return html

# -------- EDITAR CLIENTE + GERENCIAR IMEIs --------
@app.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):

    conn = conectar()
    cur = conn.cursor()

    if request.method == "POST" and "salvar_cliente" in request.form:
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        email = request.form["email"]
        telefone = request.form["telefone"]

        cur.execute("""
            UPDATE clientes
            SET nome=%s, cpf=%s, email=%s, telefone=%s
            WHERE id=%s
        """, (nome, cpf, email, telefone, id))

        conn.commit()

    if request.method == "POST" and "novo_imei" in request.form:
        novo_imei = request.form["novo_imei"]

        cur.execute("""
            INSERT INTO imeis (cliente_id, imei)
            VALUES (%s, %s)
        """, (id, novo_imei))

        conn.commit()

    cur.execute("SELECT nome, cpf, email, telefone FROM clientes WHERE id=%s", (id,))
    cliente = cur.fetchone()

    cur.execute("SELECT id, imei FROM imeis WHERE cliente_id=%s", (id,))
    lista_imeis = cur.fetchall()

    cur.close()
    conn.close()

    html = f"""
    <h2>Editar Cliente</h2>

    <form method="POST">
        Nome: <input name="nome" value="{cliente[0]}" required><br><br>
        CPF: <input name="cpf" value="{cliente[1]}" required><br><br>
        Email: <input name="email" value="{cliente[2]}"><br><br>
        Telefone: <input name="telefone" value="{cliente[3]}"><br><br>

        <button type="submit" name="salvar_cliente">Salvar Alterações</button>
    </form>

    <hr>
    <h3>IMEIs Cadastrados</h3>
    """

    if lista_imeis:
        for i in lista_imeis:
            html += f"""
            {i[1]}
            <a href="/imeis/excluir/{i[0]}/{id}">
                <button>Excluir</button>
            </a>
            <br><br>
            """
    else:
        html += "Nenhum IMEI cadastrado.<br><br>"

    html += f"""
    <hr>
    <h3>Adicionar Novo IMEI</h3>
    <form method="POST">
        <input name="novo_imei" required>
        <button type="submit">Adicionar IMEI</button>
    </form>

    <br>
    <a href="/clientes/listar"><button>Voltar</button></a>
    """

    return html

# -------- EXCLUIR CLIENTE --------
@app.route("/clientes/excluir/<int:id>")
def excluir_cliente(id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/clientes/listar")

# -------- EXCLUIR IMEI --------
@app.route("/imeis/excluir/<int:imei_id>/<int:cliente_id>")
def excluir_imei(imei_id, cliente_id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("DELETE FROM imeis WHERE id=%s", (imei_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(f"/clientes/editar/{cliente_id}")

# -------- PESQUISAR --------
@app.route("/clientes/pesquisar", methods=["GET", "POST"])
def pesquisar():

    if request.method == "POST":
        termo = request.form["termo"]

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            SELECT c.nome, c.cpf, i.imei
            FROM clientes c
            LEFT JOIN imeis i ON c.id = i.cliente_id
            WHERE c.cpf=%s OR i.imei=%s
        """, (termo, termo))

        dados = cur.fetchall()

        cur.close()
        conn.close()

        html = "<h2>Resultado</h2>"
        html += "<a href='/clientes'><button>Voltar</button></a><hr>"

        for d in dados:
            html += f"""
            Nome: {d[0]} <br>
            CPF: {d[1]} <br>
            IMEI: {d[2]} <br><hr>
            """

        return html

    return """
    <h2>Pesquisar por CPF ou IMEI</h2>
    <form method="POST">
        <input name="termo" required>
        <button type="submit">Pesquisar</button>
    </form>
    <a href="/clientes"><button>Voltar</button></a>
    """

# ================= FUNCIONÁRIOS =================
@app.route("/funcionarios")
def funcionarios_menu():
    return """
    <h1>Funcionários</h1>
    <a href="/"><button>Voltar</button></a>
    <a href="/funcionarios/cadastrar"><button>Cadastrar</button></a>
    <a href="/funcionarios/listar"><button>Listar</button></a>
    """

@app.route("/funcionarios/cadastrar", methods=["GET", "POST"])
def cadastrar_funcionario():
    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        email = request.form["email"]
        telefone = request.form["telefone"]

        conn = conectar()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO funcionarios (nome, cpf, email, telefone)
            VALUES (%s, %s, %s, %s)
        """, (nome, cpf, email, telefone))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/funcionarios/listar")

    return """
    <h2>Cadastrar Funcionário</h2>
    <form method="POST">
        Nome: <input name="nome" required><br><br>
        CPF: <input name="cpf" required><br><br>
        Email: <input name="email"><br><br>
        Telefone: <input name="telefone"><br><br>
        <button type="submit">Salvar</button>
    </form>
    <a href="/funcionarios"><button>Voltar</button></a>
    """

@app.route("/funcionarios/listar")
def listar_funcionarios():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id, nome, cpf, email, telefone FROM funcionarios")
    dados = cur.fetchall()

    cur.close()
    conn.close()

    html = "<h2>Lista de Funcionários</h2>"
    html += "<a href='/funcionarios'><button>Voltar</button></a><hr>"

    for d in dados:
        html += f"""
        ID: {d[0]} <br>
        Nome: {d[1]} <br>
        CPF: {d[2]} <br>
        Email: {d[3]} <br>
        Telefone: {d[4]} <br>
        <a href='/funcionarios/excluir/{d[0]}'><button>Excluir</button></a>
        <hr>
        """

    return html

@app.route("/funcionarios/excluir/<int:id>")
def excluir_funcionario(id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("DELETE FROM funcionarios WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect("/funcionarios/listar")


if __name__ == "__main__":
    app.run(debug=True)