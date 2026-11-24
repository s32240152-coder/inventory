"""Fungsi bantu (padanan includes/functions.php)."""
from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def staff_required(view):
    """Hanya petugas (admin & staff). Konsumen diarahkan ke katalog."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        if session.get("role") not in ("admin", "staff"):
            flash("Halaman ini hanya untuk petugas.", "warning")
            return redirect(url_for("shop"))
        return view(*args, **kwargs)

    return wrapped


def customer_required(view):
    """Hanya konsumen. Petugas diarahkan ke dashboard."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "customer":
            flash("Halaman ini khusus konsumen.", "warning")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Aksi ini hanya untuk admin.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped


def rupiah(value):
    """Format angka ke Rp 1.250.000"""
    try:
        return "Rp " + f"{float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
