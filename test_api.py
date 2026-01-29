"""
3D Yazıcı Maliyet Hesaplayıcı - API Testleri
pytest ile temel API testleri
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

def test_health_check():
    """Health check endpoint testi."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


# =============================================================================
# SETTINGS TESTS
# =============================================================================

def test_get_settings():
    """Ayarları getirme testi."""
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert "currency_rates" in data
    assert "energy" in data
    assert "cost_parameters" in data
    assert "materials" in data


# =============================================================================
# MATERIAL TESTS
# =============================================================================

def test_get_materials():
    """Malzeme listesi testi."""
    response = client.get("/materials")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_delete_material():
    """Malzeme ekleme ve silme testi."""
    # Yeni malzeme ekle
    new_material = {
        "name": "Test Material",
        "price": 500.0,
        "weight_g": 1000
    }
    response = client.post("/materials", json=new_material)
    assert response.status_code == 201
    
    # Malzemeyi sil
    response = client.delete("/materials/Test Material")
    assert response.status_code == 200


def test_create_duplicate_material_fails():
    """Aynı isimde malzeme ekleme hatası testi."""
    # Önce varolan malzeme listesini kontrol et
    response = client.get("/materials")
    materials = response.json()
    
    if materials:
        # Varolan bir malzeme adıyla eklemeye çalış
        duplicate = {
            "name": materials[0]["name"],
            "price": 100.0,
            "weight_g": 1000
        }
        response = client.post("/materials", json=duplicate)
        assert response.status_code == 400


# =============================================================================
# PRINTER TESTS
# =============================================================================

def test_get_printers():
    """Yazıcı listesi testi."""
    response = client.get("/printers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_get_update_delete_printer():
    """Yazıcı CRUD testi."""
    # Yeni yazıcı ekle
    new_printer = {
        "name": "Test Printer",
        "brand": "Test Brand",
        "model": "Test Model",
        "nozzle_lifespan_hours": 500,
        "nozzle_price": 200,
        "heater_lifespan_hours": 1200,
        "heater_price": 250,
        "motor_lifespan_hours": 6000,
        "motor_price": 700,
        "maintenance_cost": 600
    }
    response = client.post("/printers", json=new_printer)
    assert response.status_code == 201
    
    # Yazıcıları listele ve test yazıcısını bul
    response = client.get("/printers")
    printers = response.json()
    test_printer = next((p for p in printers if p["name"] == "Test Printer"), None)
    assert test_printer is not None
    printer_id = test_printer["id"]
    
    # Yazıcı detayını al
    response = client.get(f"/printers/{printer_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Printer"
    
    # Yazıcıyı güncelle
    update_data = {"name": "Updated Printer", "brand": "Updated Brand"}
    response = client.put(f"/printers/{printer_id}", json=update_data)
    assert response.status_code == 200
    
    # Güncellemeyi doğrula
    response = client.get(f"/printers/{printer_id}")
    assert response.json()["name"] == "Updated Printer"
    
    # Yazıcıyı sil
    response = client.delete(f"/printers/{printer_id}")
    assert response.status_code == 200


def test_get_nonexistent_printer():
    """Olmayan yazıcı hatası testi."""
    response = client.get("/printers/99999")
    assert response.status_code == 404


# =============================================================================
# CUSTOMER TESTS
# =============================================================================

def test_get_customers():
    """Müşteri listesi testi."""
    response = client.get("/customers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_get_update_delete_customer():
    """Müşteri CRUD testi."""
    # Yeni müşteri ekle
    new_customer = {
        "name": "Test Customer",
        "company": "Test Company",
        "address": "Test Address",
        "phone": "123-456-7890",
        "email": "test@example.com",
        "tax_number": "1234567890"
    }
    response = client.post("/customers", json=new_customer)
    assert response.status_code == 201
    
    # Müşterileri listele ve test müşterisini bul
    response = client.get("/customers")
    customers = response.json()
    test_customer = next((c for c in customers if c["name"] == "Test Customer"), None)
    assert test_customer is not None
    customer_id = test_customer["id"]
    
    # Müşteri detayını al
    response = client.get(f"/customers/{customer_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Customer"
    
    # Müşteriyi güncelle
    update_data = {"name": "Updated Customer", "company": "Updated Company"}
    response = client.put(f"/customers/{customer_id}", json=update_data)
    assert response.status_code == 200
    
    # Güncellemeyi doğrula
    response = client.get(f"/customers/{customer_id}")
    assert response.json()["name"] == "Updated Customer"
    
    # Müşteriyi sil
    response = client.delete(f"/customers/{customer_id}")
    assert response.status_code == 200


# =============================================================================
# COST CALCULATION TESTS
# =============================================================================

def test_calculate_cost():
    """Maliyet hesaplama testi."""
    # Önce malzeme listesini al
    response = client.get("/materials")
    materials = response.json()
    
    if materials:
        request_data = {
            "material_name": materials[0]["name"],
            "print_weight_grams": 50.0,
            "print_time_minutes": 120,
            "is_first_print": True
        }
        response = client.post("/calculate-cost", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "total_cost" in data
        assert "breakdown" in data
        assert data["total_cost"] > 0


def test_calculate_cost_invalid_material():
    """Geçersiz malzeme ile maliyet hesaplama hatası testi."""
    request_data = {
        "material_name": "Nonexistent Material",
        "print_weight_grams": 50.0,
        "print_time_minutes": 120,
        "is_first_print": True
    }
    response = client.post("/calculate-cost", json=request_data)
    assert response.status_code == 404


# =============================================================================
# COMPANY INFO TESTS
# =============================================================================

def test_get_company_info():
    """Şirket bilgisi alma testi."""
    response = client.get("/company")
    assert response.status_code == 200


def test_update_company_info():
    """Şirket bilgisi güncelleme testi."""
    company_data = {
        "name": "Test Şirket",
        "address": "Test Adres",
        "phone": "123-456-7890",
        "email": "test@sirket.com",
        "tax_number": "1234567890"
    }
    response = client.put("/company", json=company_data)
    assert response.status_code == 200


# =============================================================================
# INVOICE TESTS
# =============================================================================

def test_get_invoices():
    """Fatura listesi testi."""
    response = client.get("/invoices")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
