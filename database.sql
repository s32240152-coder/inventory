-- ============================================================
-- Inventory Management System - Skema MySQL / MariaDB
--
-- Cara pakai (pilih salah satu):
--   1. phpMyAdmin (XAMPP): tab "Import" -> pilih file ini -> Go
--   2. Biarkan kosong: aplikasi akan membuat database & tabel sendiri
--      saat pertama kali dijalankan (python app.py).
-- Akun awal admin / admin123 dibuat otomatis oleh aplikasi.
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventory_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE inventory_db;

-- role: admin & staff = petugas gudang, customer = konsumen (pemesan)
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    full_name   VARCHAR(100) NOT NULL,
    password    VARCHAR(255) NOT NULL,
    role        ENUM('admin', 'staff', 'customer') NOT NULL DEFAULT 'customer',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== FILE MASTER =====
CREATE TABLE IF NOT EXISTS categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS suppliers (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    name    VARCHAR(100) NOT NULL,
    phone   VARCHAR(30)  NULL,
    address VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    code        VARCHAR(30)  NOT NULL UNIQUE,
    name        VARCHAR(150) NOT NULL,
    category_id INT NULL,
    supplier_id INT NULL,
    unit        VARCHAR(20)  NOT NULL DEFAULT 'pcs',
    price       DECIMAL(15,2) NOT NULL DEFAULT 0,
    stock       INT NOT NULL DEFAULT 0,
    min_stock   INT NOT NULL DEFAULT 5,
    CONSTRAINT chk_products_price CHECK (price >= 0),
    CONSTRAINT chk_products_stock CHECK (stock >= 0),
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id),
    CONSTRAINT fk_products_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Konsumen. user_id terisi jika konsumen punya akun login (hasil register);
-- NULL untuk konsumen yang dicatat manual oleh petugas (pembeli langsung).
CREATE TABLE IF NOT EXISTS customers (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    phone       VARCHAR(30)  NULL,
    address     VARCHAR(255) NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_customers_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== FILE TRANSAKSI =====
-- type 'in'  = barang masuk (pembelian dari supplier)
-- type 'out' = barang keluar (penjualan / pemakaian)
CREATE TABLE IF NOT EXISTS transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    product_id  INT NOT NULL,
    type        ENUM('in', 'out') NOT NULL,
    quantity    INT NOT NULL,
    price       DECIMAL(15,2) NOT NULL DEFAULT 0,
    note        VARCHAR(255) NULL,
    user_id     INT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trx_product (product_id),
    INDEX idx_trx_date (created_at),
    CONSTRAINT chk_trx_qty CHECK (quantity > 0),
    CONSTRAINT fk_trx_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_trx_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pesanan konsumen: pending -> processed (jadi barang keluar) / cancelled
CREATE TABLE IF NOT EXISTS orders (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    customer_id  INT NOT NULL,
    status       ENUM('pending', 'processed', 'cancelled') NOT NULL DEFAULT 'pending',
    note         VARCHAR(255) NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_by INT NULL,
    processed_at DATETIME NULL,
    INDEX idx_order_customer (customer_id),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
    CONSTRAINT fk_orders_user FOREIGN KEY (processed_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    order_id    INT NOT NULL,
    product_id  INT NOT NULL,
    quantity    INT NOT NULL,
    price       DECIMAL(15,2) NOT NULL DEFAULT 0,
    INDEX idx_order_items_order (order_id),
    CONSTRAINT chk_item_qty CHECK (quantity > 0),
    CONSTRAINT fk_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
