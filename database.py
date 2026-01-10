"""
3D Yazıcı Maliyet Hesaplayıcı - Veritabanı Modülü
SQLite ile yazıcı, müşteri ve fatura yönetimi
"""

import sqlite3
import os
from datetime import datetime

DB_FILE = "printer_cost.db"


def get_connection():
    """Veritabanı bağlantısı döndürür."""
    return sqlite3.connect(DB_FILE)


def init_database():
    """Veritabanı tablolarını oluşturur."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Yazıcılar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS printers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            model TEXT,
            nozzle_lifespan_hours REAL DEFAULT 400,
            nozzle_remaining_hours REAL DEFAULT 400,
            nozzle_price REAL DEFAULT 150,
            heater_lifespan_hours REAL DEFAULT 1000,
            heater_remaining_hours REAL DEFAULT 1000,
            heater_price REAL DEFAULT 200,
            motor_lifespan_hours REAL DEFAULT 5000,
            motor_remaining_hours REAL DEFAULT 5000,
            motor_price REAL DEFAULT 600,
            maintenance_cost REAL DEFAULT 500,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Müşteriler tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            tax_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Şirket bilgileri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            tax_number TEXT,
            logo_path TEXT
        )
    ''')
    
    # Faturalar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE,
            customer_id INTEGER,
            printer_id INTEGER,
            material_name TEXT,
            print_weight_g REAL,
            print_time_hours REAL,
            is_first_print INTEGER DEFAULT 1,
            material_cost REAL,
            energy_cost REAL,
            depreciation_cost REAL,
            preparation_cost REAL,
            failure_risk_cost REAL,
            special_discount REAL DEFAULT 0,
            special_discount_note TEXT,
            total_cost REAL,
            currency TEXT DEFAULT 'TRY',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (printer_id) REFERENCES printers(id)
        )
    ''')
    
    # Varsayılan şirket bilgisi ekle (yoksa)
    cursor.execute('SELECT COUNT(*) FROM company_info')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO company_info (id, name, address, phone, email, tax_number)
            VALUES (1, 'Şirket Adı', 'Adres', 'Telefon', 'email@example.com', 'Vergi No')
        ''')
    
    conn.commit()
    conn.close()


# =============================================================================
# PRINTER OPERATIONS
# =============================================================================

def add_printer(name, brand="", model="", nozzle_lifespan=400, nozzle_price=150,
                heater_lifespan=1000, heater_price=200, motor_lifespan=5000,
                motor_price=600, maintenance_cost=500):
    """Yeni yazıcı ekler."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO printers (name, brand, model, nozzle_lifespan_hours, 
            nozzle_remaining_hours, nozzle_price, heater_lifespan_hours,
            heater_remaining_hours, heater_price, motor_lifespan_hours,
            motor_remaining_hours, motor_price, maintenance_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, brand, model, nozzle_lifespan, nozzle_lifespan, nozzle_price,
          heater_lifespan, heater_lifespan, heater_price, motor_lifespan,
          motor_lifespan, motor_price, maintenance_cost))
    conn.commit()
    printer_id = cursor.lastrowid
    conn.close()
    return printer_id


def get_all_printers():
    """Tüm yazıcıları döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM printers ORDER BY name')
    printers = cursor.fetchall()
    conn.close()
    return printers


def get_printer(printer_id):
    """Belirli bir yazıcıyı döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM printers WHERE id = ?', (printer_id,))
    printer = cursor.fetchone()
    conn.close()
    return printer


def get_printer_names():
    """Dropdown için yazıcı isimlerini döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM printers ORDER BY name')
    printers = cursor.fetchall()
    conn.close()
    return printers


def update_printer_lifespan(printer_id, hours_used):
    """Yazıcının kalan ömürlerini günceller."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE printers SET
            nozzle_remaining_hours = MAX(0, nozzle_remaining_hours - ?),
            heater_remaining_hours = MAX(0, heater_remaining_hours - ?),
            motor_remaining_hours = MAX(0, motor_remaining_hours - ?)
        WHERE id = ?
    ''', (hours_used, hours_used, hours_used, printer_id))
    conn.commit()
    conn.close()


def reset_printer_component(printer_id, component):
    """Belirli bir parçanın ömrünü sıfırlar (bakım yapıldığında)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if component == 'nozzle':
        cursor.execute('''
            UPDATE printers SET nozzle_remaining_hours = nozzle_lifespan_hours
            WHERE id = ?
        ''', (printer_id,))
    elif component == 'heater':
        cursor.execute('''
            UPDATE printers SET heater_remaining_hours = heater_lifespan_hours
            WHERE id = ?
        ''', (printer_id,))
    elif component == 'motor':
        cursor.execute('''
            UPDATE printers SET motor_remaining_hours = motor_lifespan_hours
            WHERE id = ?
        ''', (printer_id,))
    
    conn.commit()
    conn.close()


def delete_printer(printer_id):
    """Yazıcıyı siler."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM printers WHERE id = ?', (printer_id,))
    conn.commit()
    conn.close()


# =============================================================================
# CUSTOMER OPERATIONS
# =============================================================================

def add_customer(name, company="", address="", phone="", email="", tax_number=""):
    """Yeni müşteri ekler."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO customers (name, company, address, phone, email, tax_number)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, company, address, phone, email, tax_number))
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    return customer_id


def get_all_customers():
    """Tüm müşterileri döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers ORDER BY name')
    customers = cursor.fetchall()
    conn.close()
    return customers


def get_customer(customer_id):
    """Belirli bir müşteriyi döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
    customer = cursor.fetchone()
    conn.close()
    return customer


def get_customer_names():
    """Dropdown için müşteri isimlerini döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, company FROM customers ORDER BY name')
    customers = cursor.fetchall()
    conn.close()
    return customers


def delete_customer(customer_id):
    """Müşteriyi siler."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()


# =============================================================================
# COMPANY INFO OPERATIONS
# =============================================================================

def get_company_info():
    """Şirket bilgilerini döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM company_info WHERE id = 1')
    info = cursor.fetchone()
    conn.close()
    return info


def update_company_info(name, address, phone, email, tax_number, logo_path=""):
    """Şirket bilgilerini günceller."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE company_info SET
            name = ?, address = ?, phone = ?, email = ?, tax_number = ?, logo_path = ?
        WHERE id = 1
    ''', (name, address, phone, email, tax_number, logo_path))
    conn.commit()
    conn.close()


# =============================================================================
# INVOICE OPERATIONS
# =============================================================================

def generate_invoice_number():
    """Benzersiz fatura numarası oluşturur."""
    now = datetime.now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM invoices WHERE created_at LIKE ?', 
                   (f'{now.strftime("%Y-%m-%d")}%',))
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"FTR-{now.strftime('%Y%m%d')}-{count:04d}"


def save_invoice(customer_id, printer_id, material_name, print_weight_g, 
                 print_time_hours, is_first_print, material_cost, energy_cost,
                 depreciation_cost, preparation_cost, failure_risk_cost,
                 special_discount, special_discount_note, total_cost, currency="TRY"):
    """Faturayı veritabanına kaydeder."""
    conn = get_connection()
    cursor = conn.cursor()
    invoice_number = generate_invoice_number()
    
    cursor.execute('''
        INSERT INTO invoices (invoice_number, customer_id, printer_id, material_name,
            print_weight_g, print_time_hours, is_first_print, material_cost,
            energy_cost, depreciation_cost, preparation_cost, failure_risk_cost,
            special_discount, special_discount_note, total_cost, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (invoice_number, customer_id, printer_id, material_name, print_weight_g,
          print_time_hours, 1 if is_first_print else 0, material_cost, energy_cost,
          depreciation_cost, preparation_cost, failure_risk_cost, special_discount,
          special_discount_note, total_cost, currency))
    
    conn.commit()
    invoice_id = cursor.lastrowid
    conn.close()
    return invoice_id, invoice_number


def get_invoice(invoice_id):
    """Belirli bir faturayı döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.*, c.name as customer_name, c.company, c.address, 
               c.phone, c.email, c.tax_number,
               p.name as printer_name
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN printers p ON i.printer_id = p.id
        WHERE i.id = ?
    ''', (invoice_id,))
    invoice = cursor.fetchone()
    conn.close()
    return invoice


def get_all_invoices():
    """Tüm faturaları döndürür."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.id, i.invoice_number, c.name, i.total_cost, i.created_at
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        ORDER BY i.created_at DESC
    ''')
    invoices = cursor.fetchall()
    conn.close()
    return invoices


# Veritabanını başlat
init_database()
