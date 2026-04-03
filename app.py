from flask import Flask, render_template, request, redirect, session
import sqlite3, datetime

app = Flask(__name__)
app.secret_key = "profinal"

def db():
    return sqlite3.connect("database.db")

# 🔐 LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["usuario"]
        pwd = request.form["password"]

        usuarios = {
            "admin": {"password":"1234","rol":"admin"},
            "cajero": {"password":"1234","rol":"cajero"},
            "cocina": {"password":"1234","rol":"cocina"}
        }

        if user in usuarios and usuarios[user]["password"] == pwd:
            session["user"] = user
            session["rol"] = usuarios[user]["rol"]
            return redirect("/")

    return render_template("login.html")

# 🏠 HOME
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")

    con = db()
    productos = con.execute("SELECT * FROM productos").fetchall()
    carrito = session.get("carrito", [])
    total = sum(i["precio"]*i["cantidad"] for i in carrito)

    return render_template("ventas.html", productos=productos, carrito=carrito, total=total)

# ➕
@app.route("/sumar/<int:id>")
def sumar(id):
    carrito = session.get("carrito", [])
    for i in carrito:
        if i["id"] == id:
            i["cantidad"] += 1
    session["carrito"] = carrito
    return redirect("/")

# ➖
@app.route("/restar/<int:id>")
def restar(id):
    carrito = session.get("carrito", [])
    for i in carrito:
        if i["id"] == id:
            i["cantidad"] -= 1
    carrito = [x for x in carrito if x["cantidad"] > 0]
    session["carrito"] = carrito
    return redirect("/")

# 🛒 AGREGAR
@app.route("/add/<int:id>")
def add(id):
    con = db()
    p = con.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()

    carrito = session.get("carrito", [])

    for i in carrito:
        if i["id"] == id:
            i["cantidad"] += 1
            break
    else:
        carrito.append({"id":p[0],"nombre":p[1],"precio":p[2],"cantidad":1})

    session["carrito"] = carrito
    return redirect("/")

# 💥 FINALIZAR VENTA + DESCONTAR INGREDIENTES
@app.route("/finish")
def finish():
    con = db()
    carrito = session.get("carrito", [])

    total = 0
    detalle = []

    for item in carrito:
        total += item["precio"] * item["cantidad"]

        # guardar venta
        for _ in range(item["cantidad"]):
            con.execute("INSERT INTO ventas(producto_id,fecha) VALUES(?,?)",
                        (item["id"], datetime.datetime.now()))

        # 🔻 descontar ingredientes
        recetas = con.execute(
            "SELECT ingrediente_id, cantidad FROM recetas WHERE producto_id=?",
            (item["id"],)
        ).fetchall()

        for r in recetas:
            con.execute(
                "UPDATE ingredientes SET cantidad = cantidad - ? WHERE id=?",
                (r[1]*item["cantidad"], r[0])
            )

        detalle.append(item)

    con.commit()

    session["ticket"] = {
        "detalle": detalle,
        "total": total,
        "fecha": str(datetime.datetime.now())
    }

    session["carrito"] = []

    return redirect("/ticket")

# 🧾 TICKET
@app.route("/ticket")
def ticket():
    return render_template("ticket.html")

# 📊 REPORTES
@app.route("/reportes")
def reportes():
    if session.get("rol") != "admin":
        return "❌ No tienes permiso"

    con = db()
    data = con.execute("""
        SELECT p.nombre, COUNT(*) cantidad, SUM(p.precio) total
        FROM ventas v
        JOIN productos p ON v.producto_id=p.id
        GROUP BY p.nombre
    """).fetchall()

    return render_template("reportes.html", data=data)

# 📦 INVENTARIO
@app.route("/inventario")
def inventario():
    if session.get("rol") != "admin":
        return "❌ No tienes permiso"

    con = db()
    datos = con.execute("SELECT * FROM ingredientes").fetchall()
    return render_template("inventario.html", datos=datos)

# 👨‍🍳 COCINA
@app.route("/cocina")
def cocina():
    if session.get("rol") not in ["admin","cocina"]:
        return "❌ No tienes permiso"

    con = db()
    ventas = con.execute("""
        SELECT p.nombre, COUNT(*) cantidad
        FROM ventas v
        JOIN productos p ON v.producto_id=p.id
        GROUP BY p.nombre
    """).fetchall()

    return render_template("cocina.html", ventas=ventas)

# 🚪 LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run()