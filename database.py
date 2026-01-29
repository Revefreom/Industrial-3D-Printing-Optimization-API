"""
3D Yazıcı Maliyet Hesaplayıcı - Veritabanı Modülü
SQLite ile yazıcı, müşteri ve fatura yönetimi
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from config import get_settings, logger

settings = get_settings()
DB_FILE = settings.DB_FILE


class DatabaseError(Exception):
    """Veritabanı işlem hataları için custom exception."""
    pass


@contextmanager
def get_connection():
    """
    Context manager ile veritabanı bağlantısı.
    Otomatik commit/rollback ve connection close sağlar.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Veritabanı hatası: {e}")
        raise DatabaseError(f"Veritabanı işlemi başarısız: {e}")
    finally:
        if conn:
            conn.close()


def init_database():
    """Veritabanı tablolarını oluşturur."""
    logger.info("Veritabanı başlatılıyor...")
    
    with get_connection() as conn:
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
    
    logger.info("Veritabanı başarıyla başlatıldı.")


# =============================================================================
# PRINTER OPERATIONS
# =============================================================================

def add_printer(name, brand="", model="", nozzle_lifespan=400, nozzle_price=150,
                heater_lifespan=1000, heater_price=200, motor_lifespan=5000,
                motor_price=600, maintenance_cost=500):
    """Yeni yazıcı ekler."""
    logger.info(f"Yazıcı ekleniyor: {name}")
    with get_connection() as conn:
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
        printer_id = cursor.lastrowid
    logger.info(f"Yazıcı eklendi: ID={printer_id}")
    return printer_id


def get_all_printers():
    """Tüm yazıcıları döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM printers ORDER BY name')
        return cursor.fetchall()


def get_printer(printer_id):
    """Belirli bir yazıcıyı döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM printers WHERE id = ?', (printer_id,))
        return cursor.fetchone()


def get_printer_names():
    """Dropdown için yazıcı isimlerini döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM printers ORDER BY name')
        return cursor.fetchall()


def update_printer(printer_id, name=None, brand=None, model=None,
                   nozzle_lifespan=None, nozzle_price=None,
                   heater_lifespan=None, heater_price=None,
                   motor_lifespan=None, motor_price=None,
                   maintenance_cost=None):
    """Yazıcı bilgilerini günceller."""
    logger.info(f"Yazıcı güncelleniyor: ID={printer_id}")
    
    # Sadece sağlanan değerleri güncelle
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if brand is not None:
        updates.append("brand = ?")
        params.append(brand)
    if model is not None:
        updates.append("model = ?")
        params.append(model)
    if nozzle_lifespan is not None:
        updates.append("nozzle_lifespan_hours = ?")
        params.append(nozzle_lifespan)
    if nozzle_price is not None:
        updates.append("nozzle_price = ?")
        params.append(nozzle_price)
    if heater_lifespan is not None:
        updates.append("heater_lifespan_hours = ?")
        params.append(heater_lifespan)
    if heater_price is not None:
        updates.append("heater_price = ?")
        params.append(heater_price)
    if motor_lifespan is not None:
        updates.append("motor_lifespan_hours = ?")
        params.append(motor_lifespan)
    if motor_price is not None:
        updates.append("motor_price = ?")
        params.append(motor_price)
    if maintenance_cost is not None:
        updates.append("maintenance_cost = ?")
        params.append(maintenance_cost)
    
    if not updates:
        return False
    
    params.append(printer_id)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE printers SET {", ".join(updates)}
            WHERE id = ?
        ''', params)
        return cursor.rowcount > 0


def update_printer_lifespan(printer_id, hours_used):
    """Yazıcının kalan ömürlerini günceller."""
    logger.debug(f"Yazıcı ömrü güncelleniyor: ID={printer_id}, saat={hours_used}")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE printers SET
                nozzle_remaining_hours = MAX(0, nozzle_remaining_hours - ?),
                heater_remaining_hours = MAX(0, heater_remaining_hours - ?),
                motor_remaining_hours = MAX(0, motor_remaining_hours - ?)
            WHERE id = ?
        ''', (hours_used, hours_used, hours_used, printer_id))


def reset_printer_component(printer_id, component):
    """Belirli bir parçanın ömrünü sıfırlar (bakım yapıldığında)."""
    logger.info(f"Parça sıfırlanıyor: yazıcı={printer_id}, parça={component}")
    with get_connection() as conn:
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


def delete_printer(printer_id):
    """Yazıcıyı siler."""
    logger.info(f"Yazıcı siliniyor: ID={printer_id}")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM printers WHERE id = ?', (printer_id,))


# =============================================================================
# CUSTOMER OPERATIONS
# =============================================================================

def add_customer(name, company="", address="", phone="", email="", tax_number=""):
    """Yeni müşteri ekler."""
    logger.info(f"Müşteri ekleniyor: {name}")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customers (name, company, address, phone, email, tax_number)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, company, address, phone, email, tax_number))
        customer_id = cursor.lastrowid
    logger.info(f"Müşteri eklendi: ID={customer_id}")
    return customer_id


def get_all_customers():
    """Tüm müşterileri döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers ORDER BY name')
        return cursor.fetchall()


def get_customer(customer_id):
    """Belirli bir müşteriyi döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        return cursor.fetchone()


def get_customer_names():
    """Dropdown için müşteri isimlerini döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, company FROM customers ORDER BY name')
        return cursor.fetchall()


def update_customer(customer_id, name=None, company=None, address=None,
                    phone=None, email=None, tax_number=None):
    """Müşteri bilgilerini günceller."""
    logger.info(f"Müşteri güncelleniyor: ID={customer_id}")
    
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if company is not None:
        updates.append("company = ?")
        params.append(company)
    if address is not None:
        updates.append("address = ?")
        params.append(address)
    if phone is not None:
        updates.append("phone = ?")
        params.append(phone)
    if email is not None:
        updates.append("email = ?")
        params.append(email)
    if tax_number is not None:
        updates.append("tax_number = ?")
        params.append(tax_number)
    
    if not updates:
        return False
    
    params.append(customer_id)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE customers SET {", ".join(updates)}
            WHERE id = ?
        ''', params)
        return cursor.rowcount > 0


def delete_customer(customer_id):
    """Müşteriyi siler."""
    logger.info(f"Müşteri siliniyor: ID={customer_id}")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))


# =============================================================================
# COMPANY INFO OPERATIONS
# =============================================================================

def get_company_info():
    """Şirket bilgilerini döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM company_info WHERE id = 1')
        return cursor.fetchone()


def update_company_info(name, address, phone, email, tax_number, logo_path=""):
    """Şirket bilgilerini günceller."""
    logger.info("Şirket bilgileri güncelleniyor")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE company_info SET
                name = ?, address = ?, phone = ?, email = ?, tax_number = ?, logo_path = ?
            WHERE id = 1
        ''', (name, address, phone, email, tax_number, logo_path))


# =============================================================================
# INVOICE OPERATIONS
# =============================================================================

def generate_invoice_number():
    """Benzersiz fatura numarası oluşturur."""
    now = datetime.now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM invoices WHERE created_at LIKE ?', 
                       (f'{now.strftime("%Y-%m-%d")}%',))
        count = cursor.fetchone()[0] + 1
    return f"FTR-{now.strftime('%Y%m%d')}-{count:04d}"


def save_invoice(customer_id, printer_id, material_name, print_weight_g, 
                 print_time_hours, is_first_print, material_cost, energy_cost,
                 depreciation_cost, preparation_cost, failure_risk_cost,
                 special_discount, special_discount_note, total_cost, currency="TRY"):
    """Faturayı veritabanına kaydeder."""
    logger.info(f"Fatura kaydediliyor: müşteri={customer_id}")
    invoice_number = generate_invoice_number()
    
    with get_connection() as conn:
        cursor = conn.cursor()
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
        invoice_id = cursor.lastrowid
    
    logger.info(f"Fatura kaydedildi: {invoice_number}")
    return invoice_id, invoice_number


def get_invoice(invoice_id):
    """Belirli bir faturayı döndürür."""
    with get_connection() as conn:
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
        return cursor.fetchone()


def get_all_invoices():
    """Tüm faturaları döndürür."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.id, i.invoice_number, c.name, i.total_cost, i.created_at
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            ORDER BY i.created_at DESC
        ''')
        return cursor.fetchall()


# Veritabanını başlat
init_database()

