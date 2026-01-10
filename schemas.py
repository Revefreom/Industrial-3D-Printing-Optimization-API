"""
3D Yazıcı Maliyet Hesaplayıcı - Pydantic Schemas
FastAPI için veri doğrulama modelleri
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# =============================================================================
# COST CALCULATION MODELS
# =============================================================================

class CostCalculationRequest(BaseModel):
    """Maliyet hesaplama isteği için girdi modeli."""
    material_name: str = Field(..., description="Malzeme adı (örn: 'PLA - Standart')")
    print_weight_grams: float = Field(..., gt=0, description="Baskı ağırlığı (gram)")
    print_time_minutes: int = Field(..., gt=0, description="Baskı süresi (dakika)")
    printer_id: Optional[int] = Field(None, description="Yazıcı ID (opsiyonel)")
    is_first_print: bool = Field(True, description="İlk baskı mı? (Risk katsayısı için)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "material_name": "PLA - Standart",
                    "print_weight_grams": 50.0,
                    "print_time_minutes": 120,
                    "printer_id": 1,
                    "is_first_print": True
                }
            ]
        }
    }


class CostBreakdown(BaseModel):
    """Maliyet dökümü detayları."""
    material_cost: float = Field(..., description="Malzeme maliyeti (₺)")
    energy_cost: float = Field(..., description="Enerji maliyeti (₺)")
    depreciation_cost: float = Field(..., description="Amortisman maliyeti (₺)")
    preparation_cost: float = Field(..., description="Hazırlık/dilimleme maliyeti (₺)")
    failure_risk_cost: float = Field(..., description="Hata riski maliyeti (₺)")


class CostCalculationResponse(BaseModel):
    """Maliyet hesaplama yanıtı."""
    total_cost: float = Field(..., description="Toplam maliyet (₺)")
    breakdown: CostBreakdown
    print_time_hours: float = Field(..., description="Baskı süresi (saat)")
    print_time_minutes: int = Field(..., description="Baskı süresi (dakika)")
    material_name: str
    is_first_print: bool
    error_rate_percent: float = Field(..., description="Uygulanan hata oranı (%)")
    printer_name: Optional[str] = None
    nozzle_remaining_hours: Optional[float] = None
    heater_remaining_hours: Optional[float] = None
    motor_remaining_hours: Optional[float] = None


# =============================================================================
# PRINTER MODELS
# =============================================================================

class PrinterBase(BaseModel):
    """Yazıcı temel bilgileri."""
    name: str = Field(..., min_length=1, description="Yazıcı adı")
    brand: str = Field("", description="Marka")
    model: str = Field("", description="Model")


class PrinterCreate(PrinterBase):
    """Yazıcı oluşturma modeli."""
    nozzle_lifespan_hours: float = Field(400, gt=0, description="Nozzle ömrü (saat)")
    nozzle_price: float = Field(150, ge=0, description="Nozzle fiyatı (₺)")
    heater_lifespan_hours: float = Field(1000, gt=0, description="Isıtıcı ömrü (saat)")
    heater_price: float = Field(200, ge=0, description="Isıtıcı fiyatı (₺)")
    motor_lifespan_hours: float = Field(5000, gt=0, description="Motor ömrü (saat)")
    motor_price: float = Field(600, ge=0, description="Motor fiyatı (₺)")
    maintenance_cost: float = Field(500, ge=0, description="Genel bakım ücreti (₺)")


class PrinterResponse(PrinterBase):
    """Yazıcı yanıt modeli."""
    id: int
    nozzle_lifespan_hours: float
    nozzle_remaining_hours: float
    nozzle_price: float
    heater_lifespan_hours: float
    heater_remaining_hours: float
    heater_price: float
    motor_lifespan_hours: float
    motor_remaining_hours: float
    motor_price: float
    maintenance_cost: float


class ComponentResetRequest(BaseModel):
    """Parça ömrü sıfırlama isteği."""
    component: str = Field(..., pattern="^(nozzle|heater|motor)$", 
                           description="Sıfırlanacak parça: nozzle, heater veya motor")


class PrinterLifespanUpdate(BaseModel):
    """Yazıcı ömrü güncelleme."""
    hours_used: float = Field(..., gt=0, description="Kullanılan saat")


# =============================================================================
# CUSTOMER MODELS
# =============================================================================

class CustomerBase(BaseModel):
    """Müşteri temel bilgileri."""
    name: str = Field(..., min_length=1, description="Ad Soyad")
    company: str = Field("", description="Firma adı")
    address: str = Field("", description="Adres")
    phone: str = Field("", description="Telefon")
    email: str = Field("", description="E-posta")
    tax_number: str = Field("", description="Vergi numarası")


class CustomerCreate(CustomerBase):
    """Müşteri oluşturma modeli."""
    pass


class CustomerResponse(CustomerBase):
    """Müşteri yanıt modeli."""
    id: int
    created_at: Optional[str] = None


# =============================================================================
# MATERIAL MODELS
# =============================================================================

class MaterialBase(BaseModel):
    """Malzeme temel bilgileri."""
    name: str = Field(..., min_length=1, description="Malzeme adı")
    price: float = Field(..., gt=0, description="Fiyat (₺/kg)")
    weight_g: float = Field(1000, gt=0, description="Birim ağırlık (gram, varsayılan 1000g = 1kg)")


class MaterialCreate(MaterialBase):
    """Malzeme oluşturma modeli."""
    pass


class MaterialResponse(MaterialBase):
    """Malzeme yanıt modeli."""
    pass


# =============================================================================
# SETTINGS MODELS
# =============================================================================

class CurrencyRates(BaseModel):
    """Döviz kurları."""
    usd: float = Field(..., gt=0, alias="USD", description="1 USD = ? TRY")
    eur: float = Field(..., gt=0, alias="EUR", description="1 EUR = ? TRY")
    
    model_config = {"populate_by_name": True}


class EnergySettings(BaseModel):
    """Enerji ayarları."""
    price_per_kwh: float = Field(..., gt=0, description="kWh fiyatı (₺)")
    printer_watt: float = Field(..., gt=0, description="Yazıcı gücü (Watt)")


class CostParameters(BaseModel):
    """Maliyet parametreleri."""
    preparation_cost_per_hour: float = Field(..., ge=0, description="Hazırlık ücreti (₺/saat)")
    labor_cost_per_hour: float = Field(..., ge=0, description="İşçilik ücreti (₺/saat)")
    min_preparation_time_hours: float = Field(..., ge=0, description="Min. hazırlık süresi (saat)")
    first_print_error_rate: float = Field(..., ge=0, le=1, description="İlk baskı hata oranı (0-1)")
    repeat_print_error_rate: float = Field(..., ge=0, le=1, description="Tekrar baskı hata oranı (0-1)")


class AllSettings(BaseModel):
    """Tüm ayarlar."""
    currency_rates: CurrencyRates
    energy: EnergySettings
    cost_parameters: CostParameters
    materials: List[MaterialResponse]


# =============================================================================
# INVOICE MODELS
# =============================================================================

class InvoiceCreate(BaseModel):
    """Fatura oluşturma isteği."""
    customer_id: int = Field(..., description="Müşteri ID")
    printer_id: Optional[int] = Field(None, description="Yazıcı ID")
    material_name: str
    print_weight_grams: float = Field(..., gt=0)
    print_time_minutes: int = Field(..., gt=0)
    is_first_print: bool = True
    special_discount: float = Field(0, ge=0, description="Özel indirim (₺)")
    special_discount_note: str = Field("", description="İndirim notu")


class InvoiceResponse(BaseModel):
    """Fatura yanıt modeli."""
    invoice_id: int
    invoice_number: str
    date: str
    customer_name: str
    customer_company: Optional[str]
    printer_name: Optional[str]
    material_name: str
    print_weight_g: float
    print_time_hours: float
    is_first_print: bool
    material_cost: float
    energy_cost: float
    depreciation_cost: float
    preparation_cost: float
    failure_risk_cost: float
    special_discount: float
    special_discount_note: str
    total_cost: float
    currency: str


class InvoiceListItem(BaseModel):
    """Fatura listesi öğesi."""
    id: int
    invoice_number: str
    customer_name: Optional[str]
    total_cost: float
    created_at: str


# =============================================================================
# COMPANY INFO MODELS
# =============================================================================

class CompanyInfo(BaseModel):
    """Şirket bilgileri."""
    name: str = Field("", description="Şirket adı")
    address: str = Field("", description="Adres")
    phone: str = Field("", description="Telefon")
    email: str = Field("", description="E-posta")
    tax_number: str = Field("", description="Vergi numarası")


# =============================================================================
# GENERIC RESPONSE MODELS
# =============================================================================

class MessageResponse(BaseModel):
    """Genel mesaj yanıtı."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Hata yanıtı."""
    detail: str
    error_code: Optional[str] = None
