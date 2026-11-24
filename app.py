"""
Inventory Management System
Flask + MySQL  |  CRUD, Login/Register, Dashboard, Master, Transaksi, Laporan
"""
import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config.database import DBError, IntegrityError, get_db, init_db
from includes.functions import (
    admin_required,
    customer_required,
    login_required,
    rupiah,
    staff_required,
    to_float,
    to_int,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ganti-dengan-secret-key-yang-acak")
app.jinja_env.filters["rupiah"] = rupiah

init_db()


# ======================================================================
# AUTH: index / login / register / logout
# ======================================================================
def _home_for_role():
    return "shop" if session.get("role") == "customer" else "dashboard"


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for(_home_for_role()))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Selamat datang, {user['full_name']}!", "success")
            return redirect(url_for(_home_for_role()))
        flash("Username atau password salah.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not full_name or not username or not password:
            flash("Semua kolom wajib diisi.", "danger")
        elif len(password) < 6:
            flash("Password minimal 6 karakter.", "danger")
        elif password != confirm:
            flash("Konfirmasi password tidak sama.", "danger")
        else:
            db = get_db()
            try:
                # register publik = akun konsumen (akun petugas dibuat/diubah admin)
                db.execute("BEGIN")
                cur = db.execute(
                    "INSERT INTO users (username, full_name, password, role) VALUES (?, ?, ?, 'customer')",
                    (username, full_name, generate_password_hash(password)),
                )
                db.execute(
                    "INSERT INTO customers (user_id, name, phone, address) VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, full_name, phone, address),
                )
                db.commit()
                flash("Registrasi berhasil. Silakan login.", "success")
                return redirect(url_for("login"))
            except IntegrityError:
                db.rollback()
                flash("Username sudah dipakai.", "danger")
            finally:
                db.close()
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda sudah logout.", "info")
    return redirect(url_for("login"))


# ======================================================================
# DASHBOARD
# ======================================================================
@app.route("/dashboard")
@staff_required
def dashboard():
    db = get_db()
    stats = {
        "products": db.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "categories": db.execute("SELECT COUNT(*) FROM categories").fetchone()[0],
        "suppliers": db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
        "stock_value": db.execute("SELECT COALESCE(SUM(price * stock), 0) FROM products").fetchone()[0],
        "low_stock": db.execute("SELECT COUNT(*) FROM products WHERE stock <= min_stock").fetchone()[0],
        "pending_orders": db.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'").fetchone()[0],
        "trx_today": db.execute(
            "SELECT COUNT(*) FROM transactions WHERE DATE(created_at) = CURDATE()"
        ).fetchone()[0],
    }
    low_stock = db.execute(
        "SELECT code, name, stock, min_stock, unit FROM products "
        "WHERE stock <= min_stock ORDER BY stock ASC LIMIT 5"
    ).fetchall()
    recent = db.execute(
        """SELECT t.*, p.name AS product_name, p.unit
           FROM transactions t JOIN products p ON p.id = t.product_id
           ORDER BY t.id DESC LIMIT 8"""
    ).fetchall()
    db.close()
    return render_template("dashboard.html", stats=stats, low_stock=low_stock, recent=recent)


# ======================================================================
# MASTER 1: KATEGORI
# ======================================================================
@app.route("/categories", methods=["GET", "POST"])
@staff_required
def categories():
    db = get_db()
    if request.method == "POST":  # CREATE
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        if not name:
            flash("Nama kategori wajib diisi.", "danger")
        else:
            try:
                db.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, desc))
                db.commit()
                flash("Kategori berhasil ditambahkan.", "success")
            except IntegrityError:
                flash("Nama kategori sudah ada.", "danger")
        db.close()
        return redirect(url_for("categories"))

    rows = db.execute(  # READ
        """SELECT c.*, COUNT(p.id) AS total_products
           FROM categories c LEFT JOIN products p ON p.category_id = c.id
           GROUP BY c.id ORDER BY c.name"""
    ).fetchall()
    db.close()
    return render_template("categories.html", rows=rows, edit=None)


@app.route("/categories/edit/<int:cid>", methods=["GET", "POST"])
@staff_required
def category_edit(cid):
    db = get_db()
    if request.method == "POST":  # UPDATE
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        try:
            db.execute("UPDATE categories SET name = ?, description = ? WHERE id = ?", (name, desc, cid))
            db.commit()
            flash("Kategori berhasil diperbarui.", "success")
        except IntegrityError:
            flash("Nama kategori sudah ada.", "danger")
        db.close()
        return redirect(url_for("categories"))

    edit = db.execute("SELECT * FROM categories WHERE id = ?", (cid,)).fetchone()
    rows = db.execute(
        """SELECT c.*, COUNT(p.id) AS total_products
           FROM categories c LEFT JOIN products p ON p.category_id = c.id
           GROUP BY c.id ORDER BY c.name"""
    ).fetchall()
    db.close()
    if edit is None:
        flash("Data tidak ditemukan.", "danger")
        return redirect(url_for("categories"))
    return render_template("categories.html", rows=rows, edit=edit)


@app.route("/categories/delete/<int:cid>", methods=["POST"])
@staff_required
@admin_required
def category_delete(cid):  # DELETE
    db = get_db()
    try:
        db.execute("DELETE FROM categories WHERE id = ?", (cid,))
        db.commit()
        flash("Kategori dihapus.", "success")
    except IntegrityError:
        flash("Kategori tidak bisa dihapus karena masih dipakai produk.", "danger")
    db.close()
    return redirect(url_for("categories"))


# ======================================================================
# MASTER 2: SUPPLIER
# ======================================================================
@app.route("/suppliers", methods=["GET", "POST"])
@staff_required
def suppliers():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nama supplier wajib diisi.", "danger")
        else:
            db.execute(
                "INSERT INTO suppliers (name, phone, address) VALUES (?, ?, ?)",
                (name, request.form.get("phone", "").strip(), request.form.get("address", "").strip()),
            )
            db.commit()
            flash("Supplier berhasil ditambahkan.", "success")
        db.close()
        return redirect(url_for("suppliers"))

    rows = db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    db.close()
    return render_template("suppliers.html", rows=rows, edit=None)


@app.route("/suppliers/edit/<int:sid>", methods=["GET", "POST"])
@staff_required
def supplier_edit(sid):
    db = get_db()
    if request.method == "POST":
        db.execute(
            "UPDATE suppliers SET name = ?, phone = ?, address = ? WHERE id = ?",
            (
                request.form.get("name", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
                sid,
            ),
        )
        db.commit()
        db.close()
        flash("Supplier berhasil diperbarui.", "success")
        return redirect(url_for("suppliers"))

    edit = db.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
    rows = db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    db.close()
    if edit is None:
        flash("Data tidak ditemukan.", "danger")
        return redirect(url_for("suppliers"))
    return render_template("suppliers.html", rows=rows, edit=edit)


@app.route("/suppliers/delete/<int:sid>", methods=["POST"])
@staff_required
@admin_required
def supplier_delete(sid):
    db = get_db()
    try:
        db.execute("DELETE FROM suppliers WHERE id = ?", (sid,))
        db.commit()
        flash("Supplier dihapus.", "success")
    except IntegrityError:
        flash("Supplier tidak bisa dihapus karena masih dipakai produk.", "danger")
    db.close()
    return redirect(url_for("suppliers"))


# ======================================================================
# MASTER 3: PRODUK
# ======================================================================
def _product_form_data(form):
    return (
        form.get("code", "").strip().upper(),
        form.get("name", "").strip(),
        to_int(form.get("category_id")) or None,
        to_int(form.get("supplier_id")) or None,
        form.get("unit", "pcs").strip() or "pcs",
        to_float(form.get("price")),
        to_int(form.get("min_stock"), 5),
    )


def _product_list(db, keyword=""):
    sql = """SELECT p.*, c.name AS category_name, s.name AS supplier_name
             FROM products p
             LEFT JOIN categories c ON c.id = p.category_id
             LEFT JOIN suppliers s ON s.id = p.supplier_id"""
    params = ()
    if keyword:
        sql += " WHERE p.code LIKE ? OR p.name LIKE ?"
        params = (f"%{keyword}%", f"%{keyword}%")
    return db.execute(sql + " ORDER BY p.name", params).fetchall()


@app.route("/products", methods=["GET", "POST"])
@staff_required
def products():
    db = get_db()
    if request.method == "POST":  # CREATE
        code, name, cat, sup, unit, price, min_stock = _product_form_data(request.form)
        stock = max(to_int(request.form.get("stock")), 0)
        if not code or not name:
            flash("Kode dan nama produk wajib diisi.", "danger")
        elif price < 0:
            flash("Harga tidak boleh negatif.", "danger")
        else:
            try:
                db.execute(
                    """INSERT INTO products (code, name, category_id, supplier_id, unit, price, stock, min_stock)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (code, name, cat, sup, unit, price, stock, min_stock),
                )
                db.commit()
                flash("Produk berhasil ditambahkan.", "success")
            except IntegrityError:
                flash("Kode produk sudah dipakai.", "danger")
        db.close()
        return redirect(url_for("products"))

    keyword = request.args.get("q", "").strip()
    rows = _product_list(db, keyword)  # READ
    cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    sups = db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    db.close()
    return render_template("products.html", rows=rows, cats=cats, sups=sups, edit=None, q=keyword)


@app.route("/products/edit/<int:pid>", methods=["GET", "POST"])
@staff_required
def product_edit(pid):
    db = get_db()
    if request.method == "POST":  # UPDATE (stok diubah lewat transaksi)
        code, name, cat, sup, unit, price, min_stock = _product_form_data(request.form)
        try:
            db.execute(
                """UPDATE products SET code=?, name=?, category_id=?, supplier_id=?,
                   unit=?, price=?, min_stock=? WHERE id=?""",
                (code, name, cat, sup, unit, price, min_stock, pid),
            )
            db.commit()
            flash("Produk berhasil diperbarui.", "success")
        except IntegrityError:
            flash("Kode produk sudah dipakai.", "danger")
        db.close()
        return redirect(url_for("products"))

    edit = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    rows = _product_list(db)
    cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    sups = db.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    db.close()
    if edit is None:
        flash("Data tidak ditemukan.", "danger")
        return redirect(url_for("products"))
    return render_template("products.html", rows=rows, cats=cats, sups=sups, edit=edit, q="")


@app.route("/products/delete/<int:pid>", methods=["POST"])
@staff_required
@admin_required
def product_delete(pid):  # DELETE
    db = get_db()
    try:
        db.execute("DELETE FROM products WHERE id = ?", (pid,))
        db.commit()
        flash("Produk dihapus.", "success")
    except IntegrityError:
        flash("Produk tidak bisa dihapus karena sudah punya riwayat transaksi.", "danger")
    db.close()
    return redirect(url_for("products"))


# ======================================================================
# TRANSAKSI: barang masuk / barang keluar
# ======================================================================
@app.route("/transactions", methods=["GET", "POST"])
@staff_required
def transactions():
    db = get_db()
    if request.method == "POST":  # CREATE transaksi + update stok
        product_id = to_int(request.form.get("product_id"))
        trx_type = request.form.get("type")
        qty = to_int(request.form.get("quantity"))
        note = request.form.get("note", "").strip()

        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None or trx_type not in ("in", "out") or qty <= 0:
            flash("Data transaksi tidak valid.", "danger")
        elif trx_type == "out" and qty > product["stock"]:
            flash(f"Stok tidak cukup. Stok {product['name']} saat ini {product['stock']}.", "danger")
        else:
            price = to_float(request.form.get("price"), product["price"]) or product["price"]
            delta = qty if trx_type == "in" else -qty
            try:
                db.execute("BEGIN")
                db.execute(
                    "INSERT INTO transactions (product_id, type, quantity, price, note, user_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (product_id, trx_type, qty, price, note, session["user_id"]),
                )
                db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (delta, product_id))
                db.commit()
                flash("Transaksi berhasil disimpan.", "success")
            except DBError:
                db.rollback()
                flash("Gagal menyimpan transaksi.", "danger")
        db.close()
        return redirect(url_for("transactions"))

    rows = db.execute(  # READ
        """SELECT t.*, p.code, p.name AS product_name, p.unit, u.full_name AS user_name
           FROM transactions t
           JOIN products p ON p.id = t.product_id
           LEFT JOIN users u ON u.id = t.user_id
           ORDER BY t.id DESC LIMIT 100"""
    ).fetchall()
    prods = db.execute("SELECT id, code, name, stock, unit, price FROM products ORDER BY name").fetchall()
    db.close()
    return render_template("transactions.html", rows=rows, prods=prods)


@app.route("/transactions/delete/<int:tid>", methods=["POST"])
@staff_required
@admin_required
def transaction_delete(tid):  # DELETE + kembalikan stok
    db = get_db()
    trx = db.execute("SELECT * FROM transactions WHERE id = ?", (tid,)).fetchone()
    if trx is None:
        flash("Transaksi tidak ditemukan.", "danger")
    else:
        # membatalkan 'in' = stok dikurangi; membatalkan 'out' = stok dikembalikan
        delta = -trx["quantity"] if trx["type"] == "in" else trx["quantity"]
        product = db.execute("SELECT stock FROM products WHERE id = ?", (trx["product_id"],)).fetchone()
        if product["stock"] + delta < 0:
            flash("Tidak bisa dibatalkan: stok akan menjadi negatif.", "danger")
        else:
            db.execute("BEGIN")
            db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (delta, trx["product_id"]))
            db.execute("DELETE FROM transactions WHERE id = ?", (tid,))
            db.commit()
            flash("Transaksi dibatalkan dan stok disesuaikan.", "success")
    db.close()
    return redirect(url_for("transactions"))


# ======================================================================
# REPORT
# ======================================================================
@app.route("/reports")
@staff_required
def reports():
    jenis = request.args.get("jenis", "stok")
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")
    db = get_db()

    data, total = [], {}
    if jenis == "stok":
        data = _product_list(db)
        total = {
            "qty": sum(r["stock"] for r in data),
            "value": sum(r["stock"] * r["price"] for r in data),
        }
    elif jenis == "menipis":
        data = db.execute(
            """SELECT p.*, c.name AS category_name, s.name AS supplier_name
               FROM products p
               LEFT JOIN categories c ON c.id = p.category_id
               LEFT JOIN suppliers s ON s.id = p.supplier_id
               WHERE p.stock <= p.min_stock ORDER BY p.stock ASC"""
        ).fetchall()
    elif jenis == "konsumen":
        sql = """SELECT c.name, c.phone,
                        COUNT(DISTINCT o.id) AS total_orders,
                        SUM(oi.quantity) AS total_qty,
                        SUM(oi.quantity * oi.price) AS total_value
                 FROM customers c
                 JOIN orders o ON o.customer_id = c.id AND o.status = 'processed'
                 JOIN order_items oi ON oi.order_id = o.id
                 WHERE 1 = 1"""
        params = []
        if date_from:
            sql += " AND date(o.created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND date(o.created_at) <= ?"
            params.append(date_to)
        data = db.execute(sql + " GROUP BY c.id ORDER BY total_value DESC", params).fetchall()
        total = {
            "orders": sum(r["total_orders"] for r in data),
            "qty": sum(r["total_qty"] for r in data),
            "value": sum(r["total_value"] for r in data),
        }
    elif jenis in ("masuk", "keluar"):
        trx_type = "in" if jenis == "masuk" else "out"
        sql = """SELECT t.*, p.code, p.name AS product_name, p.unit, u.full_name AS user_name
                 FROM transactions t
                 JOIN products p ON p.id = t.product_id
                 LEFT JOIN users u ON u.id = t.user_id
                 WHERE t.type = ?"""
        params = [trx_type]
        if date_from:
            sql += " AND date(t.created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND date(t.created_at) <= ?"
            params.append(date_to)
        data = db.execute(sql + " ORDER BY t.created_at DESC", params).fetchall()
        total = {
            "qty": sum(r["quantity"] for r in data),
            "value": sum(r["quantity"] * r["price"] for r in data),
        }
    db.close()
    return render_template("reports.html", jenis=jenis, data=data, total=total,
                           date_from=date_from, date_to=date_to)


# ======================================================================
# MASTER 4: KONSUMEN (customer)
# ======================================================================
def _customer_list(db):
    return db.execute(
        """SELECT c.*, u.username,
                  (SELECT COUNT(*) FROM orders WHERE customer_id = c.id) AS total_orders
           FROM customers c LEFT JOIN users u ON u.id = c.user_id
           ORDER BY c.name"""
    ).fetchall()


@app.route("/customers", methods=["GET", "POST"])
@staff_required
def customers():
    db = get_db()
    if request.method == "POST":  # CREATE (konsumen tanpa akun / pembeli langsung)
        name = request.form.get("name", "").strip()
        if not name:
            flash("Nama konsumen wajib diisi.", "danger")
        else:
            db.execute(
                "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
                (name, request.form.get("phone", "").strip(), request.form.get("address", "").strip()),
            )
            db.commit()
            flash("Konsumen berhasil ditambahkan.", "success")
        db.close()
        return redirect(url_for("customers"))

    rows = _customer_list(db)  # READ
    db.close()
    return render_template("customers.html", rows=rows, edit=None)


@app.route("/customers/edit/<int:cid>", methods=["GET", "POST"])
@staff_required
def customer_edit(cid):
    db = get_db()
    if request.method == "POST":  # UPDATE
        db.execute(
            "UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?",
            (
                request.form.get("name", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
                cid,
            ),
        )
        db.commit()
        db.close()
        flash("Data konsumen diperbarui.", "success")
        return redirect(url_for("customers"))

    edit = db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    rows = _customer_list(db)
    db.close()
    if edit is None:
        flash("Data tidak ditemukan.", "danger")
        return redirect(url_for("customers"))
    return render_template("customers.html", rows=rows, edit=edit)


@app.route("/customers/delete/<int:cid>", methods=["POST"])
@staff_required
@admin_required
def customer_delete(cid):  # DELETE
    db = get_db()
    cust = db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    if cust is None:
        flash("Data tidak ditemukan.", "danger")
    elif cust["user_id"]:
        flash("Konsumen ini punya akun login, tidak bisa dihapus.", "danger")
    else:
        try:
            db.execute("DELETE FROM customers WHERE id = ?", (cid,))
            db.commit()
            flash("Konsumen dihapus.", "success")
        except IntegrityError:
            flash("Konsumen tidak bisa dihapus karena sudah punya pesanan.", "danger")
    db.close()
    return redirect(url_for("customers"))


# ======================================================================
# PENGGUNA (admin): atur peran admin / staff / customer
# ======================================================================
@app.route("/users")
@staff_required
@admin_required
def users():
    db = get_db()
    rows = db.execute("SELECT id, username, full_name, role, created_at FROM users ORDER BY id").fetchall()
    db.close()
    return render_template("users.html", rows=rows)


@app.route("/users/role/<int:uid>", methods=["POST"])
@staff_required
@admin_required
def user_role(uid):
    role = request.form.get("role")
    if role not in ("admin", "staff", "customer"):
        flash("Peran tidak valid.", "danger")
    elif uid == session["user_id"]:
        flash("Anda tidak bisa mengubah peran akun sendiri.", "danger")
    else:
        db = get_db()
        db.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))
        db.commit()
        db.close()
        flash("Peran pengguna diperbarui.", "success")
    return redirect(url_for("users"))


# ======================================================================
# KONSUMEN: katalog & pesanan
# ======================================================================
def _current_customer(db):
    """Data konsumen milik akun yang login (dibuat otomatis bila belum ada)."""
    cust = db.execute("SELECT * FROM customers WHERE user_id = ?", (session["user_id"],)).fetchone()
    if cust is None:
        db.execute(
            "INSERT INTO customers (user_id, name) VALUES (?, ?)",
            (session["user_id"], session["full_name"]),
        )
        db.commit()
        cust = db.execute("SELECT * FROM customers WHERE user_id = ?", (session["user_id"],)).fetchone()
    return cust


def _orders_with_lines(db, where="", params=()):
    """Daftar pesanan + rincian barangnya (kunci 'lines')."""
    orders = db.execute(
        f"""SELECT o.*, c.name AS customer_name, c.phone AS customer_phone,
                   COALESCE((SELECT SUM(quantity * price) FROM order_items WHERE order_id = o.id), 0) AS total
            FROM orders o JOIN customers c ON c.id = o.customer_id
            {where} ORDER BY o.id DESC""",
        params,
    ).fetchall()
    result = [dict(o, lines=[]) for o in orders]
    if not result:
        return result

    by_id = {o["id"]: o for o in result}
    marks = ",".join("?" * len(by_id))
    lines = db.execute(
        f"""SELECT oi.*, p.code, p.name, p.unit, p.stock
            FROM order_items oi JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id IN ({marks}) ORDER BY oi.id""",
        list(by_id),
    ).fetchall()
    for line in lines:
        by_id[line["order_id"]]["lines"].append(line)
    return result


@app.route("/shop", methods=["GET", "POST"])
@customer_required
def shop():
    db = get_db()
    if request.method == "POST":  # CREATE pesanan
        cust = _current_customer(db)
        prods = db.execute("SELECT id, name, price, stock, unit FROM products WHERE stock > 0").fetchall()
        items, errors = [], []
        for p in prods:
            qty = to_int(request.form.get(f"qty_{p['id']}"))
            if qty <= 0:
                continue
            if qty > p["stock"]:
                errors.append(f"{p['name']} (tersedia {p['stock']} {p['unit']})")
            else:
                items.append((p["id"], qty, p["price"]))

        if errors:
            flash("Jumlah melebihi stok: " + "; ".join(errors), "danger")
        elif not items:
            flash("Isi jumlah minimal pada satu produk.", "warning")
        else:
            db.execute("BEGIN")
            cur = db.execute(
                "INSERT INTO orders (customer_id, note) VALUES (?, ?)",
                (cust["id"], request.form.get("note", "").strip()),
            )
            db.executemany(
                "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                [(cur.lastrowid, pid, qty, price) for pid, qty, price in items],
            )
            db.commit()
            flash(f"Pesanan #{cur.lastrowid} berhasil dibuat. Menunggu diproses petugas.", "success")
            db.close()
            return redirect(url_for("my_orders"))
        db.close()
        return redirect(url_for("shop"))

    keyword = request.args.get("q", "").strip()
    rows = _product_list(db, keyword)
    db.close()
    return render_template("shop.html", rows=rows, q=keyword)


@app.route("/my-orders")
@customer_required
def my_orders():
    db = get_db()
    cust = _current_customer(db)
    orders = _orders_with_lines(db, "WHERE o.customer_id = ?", (cust["id"],))
    db.close()
    return render_template("my_orders.html", orders=orders)


@app.route("/my-orders/cancel/<int:oid>", methods=["POST"])
@customer_required
def my_order_cancel(oid):
    db = get_db()
    cust = _current_customer(db)
    cur = db.execute(
        "UPDATE orders SET status = 'cancelled' WHERE id = ? AND customer_id = ? AND status = 'pending'",
        (oid, cust["id"]),
    )
    db.commit()
    db.close()
    if cur.rowcount:
        flash(f"Pesanan #{oid} dibatalkan.", "success")
    else:
        flash("Pesanan tidak bisa dibatalkan.", "danger")
    return redirect(url_for("my_orders"))


# ======================================================================
# PETUGAS: pesanan konsumen -> diproses menjadi barang keluar
# ======================================================================
@app.route("/orders")
@staff_required
def orders():
    status = request.args.get("status", "pending")
    db = get_db()
    if status in ("pending", "processed", "cancelled"):
        rows = _orders_with_lines(db, "WHERE o.status = ?", (status,))
    else:
        status = "all"
        rows = _orders_with_lines(db)
    db.close()
    return render_template("orders.html", orders=rows, status=status)


@app.route("/orders/process/<int:oid>", methods=["POST"])
@staff_required
def order_process(oid):
    db = get_db()
    order = db.execute(
        "SELECT o.*, c.name AS customer_name FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?",
        (oid,),
    ).fetchone()
    if order is None or order["status"] != "pending":
        flash("Pesanan tidak ditemukan atau sudah diproses.", "danger")
    else:
        items = db.execute(
            """SELECT oi.*, p.name, p.stock FROM order_items oi
               JOIN products p ON p.id = oi.product_id WHERE oi.order_id = ?""",
            (oid,),
        ).fetchall()
        short = [
            f"{i['name']} (stok {i['stock']}, diminta {i['quantity']})"
            for i in items
            if i["quantity"] > i["stock"]
        ]
        if short:
            flash("Stok tidak cukup: " + "; ".join(short), "danger")
        else:
            try:
                db.execute("BEGIN")
                for i in items:
                    db.execute(
                        "INSERT INTO transactions (product_id, type, quantity, price, note, user_id) "
                        "VALUES (?, 'out', ?, ?, ?, ?)",
                        (i["product_id"], i["quantity"], i["price"],
                         f"Pesanan #{oid} - {order['customer_name']}", session["user_id"]),
                    )
                    db.execute(
                        "UPDATE products SET stock = stock - ? WHERE id = ?",
                        (i["quantity"], i["product_id"]),
                    )
                db.execute(
                    "UPDATE orders SET status = 'processed', processed_by = ?, "
                    "processed_at = NOW() WHERE id = ?",
                    (session["user_id"], oid),
                )
                db.commit()
                flash(f"Pesanan #{oid} diproses. Stok berkurang dan tercatat sebagai barang keluar.", "success")
            except DBError:
                db.rollback()
                flash("Gagal memproses pesanan.", "danger")
    db.close()
    return redirect(url_for("orders"))


@app.route("/orders/reject/<int:oid>", methods=["POST"])
@staff_required
def order_reject(oid):
    db = get_db()
    cur = db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ? AND status = 'pending'", (oid,))
    db.commit()
    db.close()
    flash(f"Pesanan #{oid} ditolak." if cur.rowcount else "Pesanan tidak bisa ditolak.",
          "success" if cur.rowcount else "danger")
    return redirect(url_for("orders"))


if __name__ == "__main__":
    app.run(debug=True)
