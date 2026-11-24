# Inventory Management System (Python / Flask / MySQL)

Aplikasi manajemen inventori untuk tugas proyek **CRUD berkelompok**.
Dibuat dengan **Python + Flask + MySQL** (kompatibel XAMPP/phpMyAdmin dan MariaDB).
Ada dua sisi pengguna: **petugas gudang** dan **konsumen**.

## Fitur vs ketentuan tugas

| Ketentuan tugas | Implementasi |
|---|---|
| Basis data | **MySQL** (`inventory_db`, skema di `database.sql`) |
| Login / Register / Dashboard | `/login`, `/register` (khusus konsumen), `/dashboard` (petugas), password di-hash |
| File Master | Kategori, Supplier, Produk, **Konsumen** (Create, Read, Update, Delete) |
| File Transaksi | Barang Masuk, Barang Keluar, dan **Pesanan Konsumen** (diproses jadi barang keluar) |
| File Report | Stok, stok menipis, barang masuk, barang keluar, **penjualan per konsumen** (filter tanggal + cetak) |
| Hosting gratis | Lihat bagian "Deploy ke PythonAnywhere" |

## Menjalankan di Komputer (XAMPP)

1. Buka **XAMPP Control Panel**, klik **Start** pada **MySQL**.
2. Siapkan Python:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
   pip install -r requirements.txt
   ```
3. Siapkan database, **pilih salah satu**:
   - **Otomatis** (paling mudah): langsung jalankan aplikasi. Database `inventory_db` dan semua tabel dibuat sendiri.
   - **Manual lewat phpMyAdmin**: buka http://localhost/phpmyadmin → tab **Import** → pilih `database.sql` → **Go**.
4. Jalankan:
   ```bash
   python app.py
   ```
5. Buka http://127.0.0.1:5000 dan login dengan **admin / admin123**.

### Pengaturan koneksi

Bawaan cocok untuk XAMPP (user `root`, tanpa password, host `127.0.0.1`, port `3306`).
Kalau berbeda, atur environment variable sebelum menjalankan:

| Variable | Bawaan |
|---|---|
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | `3306` |
| `DB_USER` | `root` |
| `DB_PASSWORD` | *(kosong)* |
| `DB_NAME` | `inventory_db` |

Contoh di PowerShell:
```powershell
$env:DB_PASSWORD = "passwordku"
python app.py
```

### Masalah umum

| Pesan error | Penyebab dan solusi |
|---|---|
| `Can't connect to MySQL server on '127.0.0.1'` | MySQL di XAMPP belum di-Start |
| `Access denied for user 'root'` | Password root MySQL Anda tidak kosong, isi `DB_PASSWORD` |
| `Unknown database` | Jangan ubah `DB_NAME` tanpa membuat databasenya, atau import `database.sql` dulu |

## Peran pengguna

| Peran | Cara mendapatkan | Akses |
|---|---|---|
| **admin** | Akun awal `admin` / `admin123` | Semua fitur, termasuk menghapus data dan mengatur peran di menu **Pengguna** |
| **staff** | Admin mengubah peran akun di menu Pengguna | Kelola master, transaksi, proses pesanan, laporan (tanpa hapus) |
| **customer** (konsumen) | Daftar sendiri lewat halaman Register | Hanya **Katalog Produk** dan **Pesanan Saya** |

Konsumen yang membuka halaman petugas otomatis dialihkan ke katalog.

## Alur pemesanan

1. Konsumen register, login, lalu isi jumlah di **Katalog Produk** dan klik *Buat Pesanan* (status **Menunggu**).
2. Konsumen bisa membatalkan pesanannya selama masih Menunggu.
3. Petugas membuka **Pesanan Konsumen**, lalu klik *Proses* atau *Tolak*.
4. Saat *Proses*: stok dicek, lalu otomatis tercatat sebagai **Barang Keluar** dan stok berkurang. Jika stok kurang, pesanan tidak diproses.
5. Pesanan yang sudah diproses masuk ke laporan **Penjualan per Konsumen**.

Aturan lain:
- **Barang Masuk** menambah stok, **Barang Keluar** mengurangi stok (ditolak jika stok kurang).
- Admin bisa membatalkan transaksi dan stok dikembalikan otomatis.
- Produk yang sudah bertransaksi, kategori/supplier yang dipakai produk, dan konsumen yang punya akun atau pesanan tidak bisa dihapus.

## Struktur Proyek

```
inventory_management_system/
├── app.py                 # semua route (auth, master, transaksi, pesanan, report)
├── database.sql           # skema MySQL (bisa di-import via phpMyAdmin)
├── requirements.txt
├── config/
│   └── database.py        # koneksi MySQL (PyMySQL) + inisialisasi
├── includes/
│   └── functions.py       # login_required, staff_required, customer_required, format rupiah
├── templates/             # base.html = header + footer
│   ├── base.html  login.html  register.html  dashboard.html
│   ├── categories.html  suppliers.html  products.html  customers.html
│   ├── transactions.html  orders.html  reports.html  users.html
│   └── shop.html  my_orders.html          # halaman konsumen
└── static/
    └── style.css
```

Tabel database: `users`, `categories`, `suppliers`, `products`, `customers` (master);
`transactions`, `orders`, `order_items` (transaksi).

## Deploy ke PythonAnywhere (gratis)

Akun gratis PythonAnywhere menyediakan database MySQL. Pastikan paket gratis saat ini masih memilikinya di tab **Databases**.

1. Daftar akun *Beginner* di https://www.pythonanywhere.com
2. Tab **Files** → upload semua isi folder proyek (atau upload zip lalu *unzip* lewat Bash console).
3. Tab **Databases** → buat password MySQL, lalu buat database baru bernama `inventory_db`.
   Nama lengkapnya akan menjadi `USERNAME$inventory_db`. Catat juga *Database host address*
   (bentuknya `USERNAME.mysql.pythonanywhere-services.com`).
4. Tab **Consoles** → Bash:
   ```bash
   cd ~/inventory_management_system
   pip install --user -r requirements.txt
   ```
5. Tab **Web** → **Add a new web app** → *Manual configuration* → pilih versi Python.
6. Pada **WSGI configuration file**, ganti isinya dengan:
   ```python
   import sys, os
   path = '/home/USERNAME_ANDA/inventory_management_system'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['SECRET_KEY']  = 'isi-dengan-teks-acak-yang-panjang'
   os.environ['DB_HOST']     = 'USERNAME_ANDA.mysql.pythonanywhere-services.com'
   os.environ['DB_USER']     = 'USERNAME_ANDA'
   os.environ['DB_PASSWORD'] = 'password-mysql-anda'
   os.environ['DB_NAME']     = 'USERNAME_ANDA$inventory_db'

   from app import app as application
   ```
7. Klik **Reload**. Tabel dibuat otomatis saat pertama kali dibuka, dan aplikasi aktif di
   `https://USERNAME_ANDA.pythonanywhere.com`.

> Ganti password `admin` setelah deploy, dan ganti `SECRET_KEY` dengan nilai acak.

## Saran Pembagian Tugas Kelompok

1. Database, login/register, dan hak akses peran
2. Master data (kategori, supplier, produk, konsumen)
3. Transaksi dan pesanan konsumen
4. Laporan, tampilan, dan hosting
