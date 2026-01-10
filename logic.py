"""
3D Yazıcı Maliyet Hesaplayıcı - Logic Modülü
Maliyet hesaplama ve veri yönetimi
"""

import json
import os
from database import (
    get_printer, update_printer_lifespan, get_company_info,
    save_invoice, get_customer
)

SETTINGS_FILE = "settings.json"


class CostManager:
    def __init__(self):
        self.data = {}
        self.load_data()

    def load_data(self):
        """JSON dosyasını okur, yoksa oluşturur."""
        if not os.path.exists(SETTINGS_FILE):
            print("Veri dosyası bulunamadı, varsayılanlar oluşturuluyor...")
            self._create_default_settings()
            return
        
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def _create_default_settings(self):
        """Varsayılan ayarları oluşturur."""
        self.data = {
            "app_settings": {
                "currency_rates": {"USD": 34.50, "EUR": 37.20},
                "selected_currency": "TRY"
            },
            "energy": {"price_per_kwh": 3.5, "printer_watt": 350},
            "cost_parameters": {
                "preparation_cost_per_hour": 50.0,
                "first_print_error_rate": 0.15,
                "repeat_print_error_rate": 0.02,
                "labor_cost_per_hour": 100.0,
                "min_preparation_time_hours": 0.5
            },
            "materials": [],
            "consumables": []
        }
        self.save_data()

    def save_data(self):
        """Mevcut veriyi JSON dosyasına yazar."""
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def calculate_cost(self, material_name, print_time_hours, print_weight_g,
                       printer_id=None, is_first_print=True, update_lifespan=False):
        """
        Gelişmiş maliyet hesaplama formülü:
        Toplam = (Baskı_Maliyeti × n) + C_hazırlık + (Baskı_Maliyeti × P_hata)
        
        Args:
            material_name: Malzeme adı
            print_time_hours: Baskı süresi (saat)
            print_weight_g: Baskı ağırlığı (gram)
            printer_id: Seçili yazıcı ID (opsiyonel)
            is_first_print: İlk baskı mı?
            update_lifespan: Yazıcı ömürünü güncelle?
        
        Returns:
            tuple: (toplam_maliyet, detaylar_dict)
        """
        details = {}
        
        # 1. Malzeme Maliyeti
        material = next((m for m in self.data.get("materials", []) 
                        if m["name"] == material_name), None)
        if material:
            # (Baskı Ağırlığı / 1000g) * 1kg Fiyatı
            mat_cost = (print_weight_g / material["weight_g"]) * material["price"]
            details["material_cost"] = mat_cost
        else:
            details["material_cost"] = 0.0

        # 2. Enerji Maliyeti
        energy = self.data.get("energy", {})
        kwh = (print_time_hours * energy.get("printer_watt", 350)) / 1000
        energy_cost = kwh * energy.get("price_per_kwh", 3.5)
        details["energy_cost"] = energy_cost

        # 3. Amortisman (Yazıcıya özel veya genel sarf malzemeleri)
        depreciation_cost = 0.0
        
        if printer_id:
            # Yazıcıya özel hesaplama
            printer = get_printer(printer_id)
            if printer:
                # printer: (id, name, brand, model, nozzle_lifespan, nozzle_remaining, 
                #           nozzle_price, heater_lifespan, heater_remaining, heater_price,
                #           motor_lifespan, motor_remaining, motor_price, maintenance_cost, created_at)
                
                # Nozzle amortisman
                nozzle_hourly = printer[6] / printer[4] if printer[4] > 0 else 0
                depreciation_cost += nozzle_hourly * print_time_hours
                
                # Heater amortisman
                heater_hourly = printer[9] / printer[7] if printer[7] > 0 else 0
                depreciation_cost += heater_hourly * print_time_hours
                
                # Motor amortisman
                motor_hourly = printer[12] / printer[10] if printer[10] > 0 else 0
                depreciation_cost += motor_hourly * print_time_hours
                
                details["printer_name"] = printer[1]
                details["nozzle_remaining"] = max(0, printer[5] - print_time_hours)
                details["heater_remaining"] = max(0, printer[8] - print_time_hours)
                details["motor_remaining"] = max(0, printer[11] - print_time_hours)
                
                # Yazıcı ömrünü güncelle
                if update_lifespan:
                    update_printer_lifespan(printer_id, print_time_hours)
        else:
            # Genel sarf malzemesi hesabı (eski yöntem)
            for item in self.data.get("consumables", []):
                hourly_cost = item["price"] / item["lifespan_hours"]
                depreciation_cost += hourly_cost * print_time_hours
        
        details["depreciation_cost"] = depreciation_cost

        # 4. Hazırlık/Dilimleme Maliyeti (süreye göre)
        cost_params = self.data.get("cost_parameters", {})
        prep_cost_per_hour = cost_params.get("preparation_cost_per_hour", 50.0)
        labor_cost_per_hour = cost_params.get("labor_cost_per_hour", 100.0)
        min_prep_time = cost_params.get("min_preparation_time_hours", 0.5)
        
        # Hazırlık süresi: minimum 0.5 saat + baskı süresinin %10'u
        prep_time = max(min_prep_time, print_time_hours * 0.1)
        preparation_cost = prep_time * (prep_cost_per_hour + labor_cost_per_hour)
        
        # Tekrar baskılarda hazırlık maliyeti %20'ye düşer
        if not is_first_print:
            preparation_cost *= 0.2
        
        details["preparation_cost"] = preparation_cost

        # 5. Hata Riski Maliyeti
        if is_first_print:
            error_rate = cost_params.get("first_print_error_rate", 0.15)
        else:
            error_rate = cost_params.get("repeat_print_error_rate", 0.02)
        
        # Temel baskı maliyeti (malzeme + enerji + amortisman)
        base_print_cost = details["material_cost"] + details["energy_cost"] + details["depreciation_cost"]
        failure_risk_cost = base_print_cost * error_rate
        details["failure_risk_cost"] = failure_risk_cost

        # 6. Toplam Maliyet
        total_cost = (
            details["material_cost"] +
            details["energy_cost"] +
            details["depreciation_cost"] +
            details["preparation_cost"] +
            details["failure_risk_cost"]
        )
        
        details["is_first_print"] = is_first_print
        details["print_time_hours"] = print_time_hours
        details["print_weight_g"] = print_weight_g
        details["material_name"] = material_name
        
        return total_cost, details

    def generate_invoice_data(self, cost_details, customer_id=None, printer_id=None,
                               special_discount=0, special_discount_note="", 
                               total_cost=None, save_to_db=True):
        """
        Fatura verisi oluşturur ve opsiyonel olarak veritabanına kaydeder.
        
        Returns:
            dict: Fatura verisi
        """
        from datetime import datetime
        
        invoice_data = {
            "date": datetime.now().strftime('%d.%m.%Y'),
            "material_name": cost_details.get("material_name", ""),
            "print_weight_g": cost_details.get("print_weight_g", 0),
            "print_time_hours": cost_details.get("print_time_hours", 0),
            "is_first_print": cost_details.get("is_first_print", True),
            "material_cost": cost_details.get("material_cost", 0),
            "energy_cost": cost_details.get("energy_cost", 0),
            "depreciation_cost": cost_details.get("depreciation_cost", 0),
            "preparation_cost": cost_details.get("preparation_cost", 0),
            "failure_risk_cost": cost_details.get("failure_risk_cost", 0),
            "special_discount": special_discount,
            "special_discount_note": special_discount_note,
            "currency": self.data.get("app_settings", {}).get("selected_currency", "TRY")
        }
        
        # Toplam maliyeti hesapla
        if total_cost is None:
            total_cost = (
                invoice_data["material_cost"] +
                invoice_data["energy_cost"] +
                invoice_data["depreciation_cost"] +
                invoice_data["preparation_cost"] +
                invoice_data["failure_risk_cost"] -
                special_discount
            )
        invoice_data["total_cost"] = total_cost
        
        # Müşteri bilgileri
        if customer_id:
            customer = get_customer(customer_id)
            if customer:
                invoice_data["customer_name"] = customer[1]
                invoice_data["customer_company"] = customer[2] or ""
                invoice_data["customer_address"] = customer[3] or ""
                invoice_data["customer_phone"] = customer[4] or ""
                invoice_data["customer_email"] = customer[5] or ""
        
        # Yazıcı bilgileri
        if printer_id:
            printer = get_printer(printer_id)
            if printer:
                invoice_data["printer_name"] = printer[1]
        
        # Veritabanına kaydet
        if save_to_db and customer_id:
            invoice_id, invoice_number = save_invoice(
                customer_id=customer_id,
                printer_id=printer_id,
                material_name=invoice_data["material_name"],
                print_weight_g=invoice_data["print_weight_g"],
                print_time_hours=invoice_data["print_time_hours"],
                is_first_print=invoice_data["is_first_print"],
                material_cost=invoice_data["material_cost"],
                energy_cost=invoice_data["energy_cost"],
                depreciation_cost=invoice_data["depreciation_cost"],
                preparation_cost=invoice_data["preparation_cost"],
                failure_risk_cost=invoice_data["failure_risk_cost"],
                special_discount=special_discount,
                special_discount_note=special_discount_note,
                total_cost=invoice_data["total_cost"],
                currency=invoice_data["currency"]
            )
            invoice_data["invoice_id"] = invoice_id
            invoice_data["invoice_number"] = invoice_number
        
        return invoice_data

    def get_material_names(self):
        """Arayüzdeki Dropdown için sadece isimleri döndürür."""
        return [m["name"] for m in self.data.get("materials", [])]

    def update_currency(self, usd_rate, eur_rate):
        """Döviz kurlarını günceller ve kaydeder."""
        self.data["app_settings"]["currency_rates"]["USD"] = float(usd_rate)
        self.data["app_settings"]["currency_rates"]["EUR"] = float(eur_rate)
        self.save_data()
        
    def convert_price(self, try_price, target_currency):
        """TRY fiyatını hedef kura çevirir."""
        if target_currency == "TRY":
            return try_price
        
        rate = self.data["app_settings"]["currency_rates"].get(target_currency, 1.0)
        return try_price / rate

    # ==========================================================================
    # MATERIAL MANAGEMENT
    # ==========================================================================
    
    def add_material(self, name, price, weight_g=1000):
        """Yeni malzeme ekler."""
        if "materials" not in self.data:
            self.data["materials"] = []
        self.data["materials"].append({
            "name": name,
            "price": float(price),
            "weight_g": float(weight_g)
        })
        self.save_data()
    
    def update_material(self, old_name, new_name, new_price, new_weight_g=1000):
        """Malzeme günceller."""
        for mat in self.data.get("materials", []):
            if mat["name"] == old_name:
                mat["name"] = new_name
                mat["price"] = float(new_price)
                mat["weight_g"] = float(new_weight_g)
                break
        self.save_data()
    
    def delete_material(self, name):
        """Malzeme siler."""
        self.data["materials"] = [m for m in self.data.get("materials", []) 
                                   if m["name"] != name]
        self.save_data()

    # ==========================================================================
    # COST PARAMETERS MANAGEMENT
    # ==========================================================================
    
    def get_cost_parameters(self):
        """Maliyet parametrelerini döndürür."""
        return self.data.get("cost_parameters", {})
    
    def update_cost_parameters(self, prep_cost, first_error_rate, repeat_error_rate, 
                                labor_cost, min_prep_time):
        """Maliyet parametrelerini günceller."""
        if "cost_parameters" not in self.data:
            self.data["cost_parameters"] = {}
        
        self.data["cost_parameters"]["preparation_cost_per_hour"] = float(prep_cost)
        self.data["cost_parameters"]["first_print_error_rate"] = float(first_error_rate)
        self.data["cost_parameters"]["repeat_print_error_rate"] = float(repeat_error_rate)
        self.data["cost_parameters"]["labor_cost_per_hour"] = float(labor_cost)
        self.data["cost_parameters"]["min_preparation_time_hours"] = float(min_prep_time)
        self.save_data()

    # ==========================================================================
    # ENERGY SETTINGS
    # ==========================================================================
    
    def get_energy_settings(self):
        """Enerji ayarlarını döndürür."""
        return self.data.get("energy", {})
    
    def update_energy_settings(self, price_per_kwh, printer_watt):
        """Enerji ayarlarını günceller."""
        if "energy" not in self.data:
            self.data["energy"] = {}
        
        self.data["energy"]["price_per_kwh"] = float(price_per_kwh)
        self.data["energy"]["printer_watt"] = float(printer_watt)
        self.save_data()