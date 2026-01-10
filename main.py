"""
3D Yazıcı Maliyet Hesaplayıcı - FastAPI Web Servisi
RESTful API ile maliyet hesaplama ve yönetim

Formül: C_total = Σ(M·P) + E + A·α
- M: Malzeme miktarı (gram)
- P: Birim fiyat (₺/kg)
- E: Enerji maliyeti
- A: Amortisman
- α: Risk/Tekrar katsayısı
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from logic import CostManager
from database import (
    get_printer_names, get_customer_names, add_printer, add_customer,
    get_all_printers, get_all_customers, delete_printer, delete_customer,
    get_company_info, update_company_info, get_printer, reset_printer_component,
    update_printer_lifespan, get_all_invoices, get_invoice, get_customer
)
from schemas import (
    CostCalculationRequest, CostCalculationResponse, CostBreakdown,
    PrinterCreate, PrinterResponse, ComponentResetRequest, PrinterLifespanUpdate,
    CustomerCreate, CustomerResponse,
    MaterialCreate, MaterialResponse,
    CurrencyRates, EnergySettings, CostParameters, AllSettings,
    InvoiceCreate, InvoiceResponse, InvoiceListItem,
    CompanyInfo, MessageResponse
)

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="3D Yazıcı Maliyet Hesaplayıcı API",
    description="""
## 3D Baskı Maliyet Hesaplama Servisi

Bu API, 3D baskı maliyetlerini profesyonel bir şekilde hesaplar.

### Maliyet Formülü
```
C_total = Σ(M·P) + E + A·α
```

- **M**: Malzeme miktarı (gram)
- **P**: Birim fiyat (₺/kg)  
- **E**: Enerji maliyeti
- **A**: Amortisman (nozzle, ısıtıcı, motor)
- **α**: Risk/Tekrar katsayısı (ilk baskı: %15, tekrar: %2)

### Özellikler
- ✅ Malzeme, enerji, amortisman hesaplama
- ✅ Yazıcı parça ömrü takibi
- ✅ Müşteri ve fatura yönetimi
- ✅ Docker uyumlu (headless)
    """,
    version="2.0.0",
    contact={
        "name": "3D Yazıcı Maliyet Hesaplayıcı",
    }
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Backend Manager
manager = CostManager()


# =============================================================================
# COST CALCULATION ENDPOINTS
# =============================================================================

@app.post(
    "/calculate-cost",
    response_model=CostCalculationResponse,
    tags=["Maliyet Hesaplama"],
    summary="3D baskı maliyeti hesapla",
    description="Malzeme, enerji, amortisman ve risk faktörlerini hesaba katarak toplam maliyeti hesaplar."
)
async def calculate_cost(request: CostCalculationRequest):
    """
    Ana maliyet hesaplama endpoint'i.
    
    Formül: C_total = Σ(M·P) + E + A·α
    """
    # Süreyi dakikadan saate çevir
    time_hours = request.print_time_minutes / 60
    
    # Malzeme kontrolü
    materials = manager.get_material_names()
    if request.material_name not in materials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Malzeme bulunamadı: '{request.material_name}'. Mevcut malzemeler: {materials}"
        )
    
    # Yazıcı kontrolü (opsiyonel)
    printer_name = None
    if request.printer_id:
        printer = get_printer(request.printer_id)
        if not printer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Yazıcı bulunamadı: ID {request.printer_id}"
            )
        printer_name = printer[1]
    
    # Maliyet hesaplama
    total, details = manager.calculate_cost(
        material_name=request.material_name,
        print_time_hours=time_hours,
        print_weight_g=request.print_weight_grams,
        printer_id=request.printer_id,
        is_first_print=request.is_first_print,
        update_lifespan=False  # Hesaplamada ömür güncellenmesin
    )
    
    # Hata oranını belirle
    cost_params = manager.get_cost_parameters()
    error_rate = cost_params.get("first_print_error_rate", 0.15) if request.is_first_print else cost_params.get("repeat_print_error_rate", 0.02)
    
    return CostCalculationResponse(
        total_cost=round(total, 2),
        breakdown=CostBreakdown(
            material_cost=round(details.get("material_cost", 0), 2),
            energy_cost=round(details.get("energy_cost", 0), 2),
            depreciation_cost=round(details.get("depreciation_cost", 0), 2),
            preparation_cost=round(details.get("preparation_cost", 0), 2),
            failure_risk_cost=round(details.get("failure_risk_cost", 0), 2)
        ),
        print_time_hours=round(time_hours, 4),
        print_time_minutes=request.print_time_minutes,
        material_name=request.material_name,
        is_first_print=request.is_first_print,
        error_rate_percent=round(error_rate * 100, 1),
        printer_name=printer_name,
        nozzle_remaining_hours=details.get("nozzle_remaining"),
        heater_remaining_hours=details.get("heater_remaining"),
        motor_remaining_hours=details.get("motor_remaining")
    )


# =============================================================================
# MATERIAL ENDPOINTS
# =============================================================================

@app.get(
    "/materials",
    response_model=List[MaterialResponse],
    tags=["Malzemeler"],
    summary="Malzeme listesi"
)
async def list_materials():
    """Tüm malzemeleri listeler."""
    materials = manager.data.get("materials", [])
    return [MaterialResponse(**m) for m in materials]


@app.post(
    "/materials",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Malzemeler"],
    summary="Yeni malzeme ekle"
)
async def create_material(material: MaterialCreate):
    """Yeni malzeme ekler."""
    # Aynı isimde malzeme var mı kontrol et
    existing = manager.get_material_names()
    if material.name in existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu isimde malzeme zaten mevcut: '{material.name}'"
        )
    
    manager.add_material(material.name, material.price, material.weight_g)
    return MessageResponse(message=f"Malzeme eklendi: {material.name}")


@app.delete(
    "/materials/{material_name}",
    response_model=MessageResponse,
    tags=["Malzemeler"],
    summary="Malzeme sil"
)
async def remove_material(material_name: str):
    """Malzeme siler."""
    existing = manager.get_material_names()
    if material_name not in existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Malzeme bulunamadı: '{material_name}'"
        )
    
    manager.delete_material(material_name)
    return MessageResponse(message=f"Malzeme silindi: {material_name}")


# =============================================================================
# PRINTER ENDPOINTS
# =============================================================================

@app.get(
    "/printers",
    response_model=List[PrinterResponse],
    tags=["Yazıcılar"],
    summary="Yazıcı listesi"
)
async def list_printers():
    """Tüm yazıcıları listeler."""
    printers = get_all_printers()
    return [
        PrinterResponse(
            id=p[0],
            name=p[1],
            brand=p[2] or "",
            model=p[3] or "",
            nozzle_lifespan_hours=p[4],
            nozzle_remaining_hours=p[5],
            nozzle_price=p[6],
            heater_lifespan_hours=p[7],
            heater_remaining_hours=p[8],
            heater_price=p[9],
            motor_lifespan_hours=p[10],
            motor_remaining_hours=p[11],
            motor_price=p[12],
            maintenance_cost=p[13]
        )
        for p in printers
    ]


@app.post(
    "/printers",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Yazıcılar"],
    summary="Yeni yazıcı ekle"
)
async def create_printer(printer: PrinterCreate):
    """Yeni yazıcı ekler."""
    printer_id = add_printer(
        name=printer.name,
        brand=printer.brand,
        model=printer.model,
        nozzle_lifespan=printer.nozzle_lifespan_hours,
        nozzle_price=printer.nozzle_price,
        heater_lifespan=printer.heater_lifespan_hours,
        heater_price=printer.heater_price,
        motor_lifespan=printer.motor_lifespan_hours,
        motor_price=printer.motor_price,
        maintenance_cost=printer.maintenance_cost
    )
    return MessageResponse(message=f"Yazıcı eklendi: {printer.name} (ID: {printer_id})")


@app.get(
    "/printers/{printer_id}",
    response_model=PrinterResponse,
    tags=["Yazıcılar"],
    summary="Yazıcı detayı"
)
async def get_printer_detail(printer_id: int):
    """Belirli bir yazıcının detaylarını döndürür."""
    p = get_printer(printer_id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yazıcı bulunamadı: ID {printer_id}"
        )
    
    return PrinterResponse(
        id=p[0],
        name=p[1],
        brand=p[2] or "",
        model=p[3] or "",
        nozzle_lifespan_hours=p[4],
        nozzle_remaining_hours=p[5],
        nozzle_price=p[6],
        heater_lifespan_hours=p[7],
        heater_remaining_hours=p[8],
        heater_price=p[9],
        motor_lifespan_hours=p[10],
        motor_remaining_hours=p[11],
        motor_price=p[12],
        maintenance_cost=p[13]
    )


@app.delete(
    "/printers/{printer_id}",
    response_model=MessageResponse,
    tags=["Yazıcılar"],
    summary="Yazıcı sil"
)
async def remove_printer(printer_id: int):
    """Yazıcı siler."""
    p = get_printer(printer_id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yazıcı bulunamadı: ID {printer_id}"
        )
    
    delete_printer(printer_id)
    return MessageResponse(message=f"Yazıcı silindi: {p[1]}")


@app.post(
    "/printers/{printer_id}/reset-component",
    response_model=MessageResponse,
    tags=["Yazıcılar"],
    summary="Parça ömrünü sıfırla"
)
async def reset_component(printer_id: int, request: ComponentResetRequest):
    """Yazıcı parçasının ömrünü sıfırlar (bakım sonrası)."""
    p = get_printer(printer_id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yazıcı bulunamadı: ID {printer_id}"
        )
    
    reset_printer_component(printer_id, request.component)
    return MessageResponse(message=f"{request.component.title()} ömrü sıfırlandı")


@app.post(
    "/printers/{printer_id}/update-lifespan",
    response_model=MessageResponse,
    tags=["Yazıcılar"],
    summary="Yazıcı ömrünü güncelle"
)
async def update_lifespan(printer_id: int, request: PrinterLifespanUpdate):
    """Baskı sonrası yazıcı parça ömürlerini düşürür."""
    p = get_printer(printer_id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yazıcı bulunamadı: ID {printer_id}"
        )
    
    update_printer_lifespan(printer_id, request.hours_used)
    
    # Güncel durumu al
    p = get_printer(printer_id)
    return MessageResponse(
        message=f"{request.hours_used} saat ömürden düşüldü. Kalan: Nozzle {p[5]:.0f}h, Isıtıcı {p[8]:.0f}h, Motor {p[11]:.0f}h"
    )


# =============================================================================
# CUSTOMER ENDPOINTS
# =============================================================================

@app.get(
    "/customers",
    response_model=List[CustomerResponse],
    tags=["Müşteriler"],
    summary="Müşteri listesi"
)
async def list_customers():
    """Tüm müşterileri listeler."""
    customers = get_all_customers()
    return [
        CustomerResponse(
            id=c[0],
            name=c[1],
            company=c[2] or "",
            address=c[3] or "",
            phone=c[4] or "",
            email=c[5] or "",
            tax_number=c[6] or "",
            created_at=c[7]
        )
        for c in customers
    ]


@app.post(
    "/customers",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Müşteriler"],
    summary="Yeni müşteri ekle"
)
async def create_customer(customer: CustomerCreate):
    """Yeni müşteri ekler."""
    customer_id = add_customer(
        name=customer.name,
        company=customer.company,
        address=customer.address,
        phone=customer.phone,
        email=customer.email,
        tax_number=customer.tax_number
    )
    return MessageResponse(message=f"Müşteri eklendi: {customer.name} (ID: {customer_id})")


@app.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    tags=["Müşteriler"],
    summary="Müşteri detayı"
)
async def get_customer_detail(customer_id: int):
    """Belirli bir müşterinin detaylarını döndürür."""
    c = get_customer(customer_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Müşteri bulunamadı: ID {customer_id}"
        )
    
    return CustomerResponse(
        id=c[0],
        name=c[1],
        company=c[2] or "",
        address=c[3] or "",
        phone=c[4] or "",
        email=c[5] or "",
        tax_number=c[6] or "",
        created_at=c[7]
    )


@app.delete(
    "/customers/{customer_id}",
    response_model=MessageResponse,
    tags=["Müşteriler"],
    summary="Müşteri sil"
)
async def remove_customer(customer_id: int):
    """Müşteri siler."""
    c = get_customer(customer_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Müşteri bulunamadı: ID {customer_id}"
        )
    
    delete_customer(customer_id)
    return MessageResponse(message=f"Müşteri silindi: {c[1]}")


# =============================================================================
# SETTINGS ENDPOINTS
# =============================================================================

@app.get(
    "/settings",
    response_model=AllSettings,
    tags=["Ayarlar"],
    summary="Tüm ayarları getir"
)
async def get_settings():
    """Tüm uygulama ayarlarını döndürür."""
    data = manager.data
    rates = data.get("app_settings", {}).get("currency_rates", {})
    energy = data.get("energy", {})
    cost_params = data.get("cost_parameters", {})
    materials = data.get("materials", [])
    
    return AllSettings(
        currency_rates=CurrencyRates(USD=rates.get("USD", 34.5), EUR=rates.get("EUR", 37.2)),
        energy=EnergySettings(
            price_per_kwh=energy.get("price_per_kwh", 3.5),
            printer_watt=energy.get("printer_watt", 350)
        ),
        cost_parameters=CostParameters(
            preparation_cost_per_hour=cost_params.get("preparation_cost_per_hour", 50),
            labor_cost_per_hour=cost_params.get("labor_cost_per_hour", 100),
            min_preparation_time_hours=cost_params.get("min_preparation_time_hours", 0.5),
            first_print_error_rate=cost_params.get("first_print_error_rate", 0.15),
            repeat_print_error_rate=cost_params.get("repeat_print_error_rate", 0.02)
        ),
        materials=[MaterialResponse(**m) for m in materials]
    )


@app.put(
    "/settings/currency",
    response_model=MessageResponse,
    tags=["Ayarlar"],
    summary="Döviz kurlarını güncelle"
)
async def update_currency(rates: CurrencyRates):
    """Döviz kurlarını günceller."""
    manager.update_currency(rates.usd, rates.eur)
    return MessageResponse(message=f"Kurlar güncellendi: 1 USD = {rates.usd} TRY, 1 EUR = {rates.eur} TRY")


@app.put(
    "/settings/energy",
    response_model=MessageResponse,
    tags=["Ayarlar"],
    summary="Enerji ayarlarını güncelle"
)
async def update_energy(settings: EnergySettings):
    """Enerji ayarlarını günceller."""
    manager.update_energy_settings(settings.price_per_kwh, settings.printer_watt)
    return MessageResponse(message=f"Enerji ayarları güncellendi: {settings.price_per_kwh} ₺/kWh, {settings.printer_watt}W")


@app.put(
    "/settings/cost-parameters",
    response_model=MessageResponse,
    tags=["Ayarlar"],
    summary="Maliyet parametrelerini güncelle"
)
async def update_cost_params(params: CostParameters):
    """Maliyet parametrelerini günceller."""
    manager.update_cost_parameters(
        params.preparation_cost_per_hour,
        params.first_print_error_rate,
        params.repeat_print_error_rate,
        params.labor_cost_per_hour,
        params.min_preparation_time_hours
    )
    return MessageResponse(message="Maliyet parametreleri güncellendi")


# =============================================================================
# COMPANY INFO ENDPOINTS
# =============================================================================

@app.get(
    "/company",
    response_model=CompanyInfo,
    tags=["Şirket"],
    summary="Şirket bilgilerini getir"
)
async def get_company():
    """Şirket bilgilerini döndürür."""
    info = get_company_info()
    if info:
        return CompanyInfo(
            name=info[1] or "",
            address=info[2] or "",
            phone=info[3] or "",
            email=info[4] or "",
            tax_number=info[5] or ""
        )
    return CompanyInfo()


@app.put(
    "/company",
    response_model=MessageResponse,
    tags=["Şirket"],
    summary="Şirket bilgilerini güncelle"
)
async def update_company(info: CompanyInfo):
    """Şirket bilgilerini günceller."""
    update_company_info(info.name, info.address, info.phone, info.email, info.tax_number)
    return MessageResponse(message="Şirket bilgileri güncellendi")


# =============================================================================
# INVOICE ENDPOINTS
# =============================================================================

@app.get(
    "/invoices",
    response_model=List[InvoiceListItem],
    tags=["Faturalar"],
    summary="Fatura listesi"
)
async def list_invoices():
    """Tüm faturaları listeler."""
    invoices = get_all_invoices()
    return [
        InvoiceListItem(
            id=inv[0],
            invoice_number=inv[1],
            customer_name=inv[2],
            total_cost=inv[3],
            created_at=inv[4]
        )
        for inv in invoices
    ]


@app.post(
    "/invoices",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Faturalar"],
    summary="Yeni fatura oluştur"
)
async def create_invoice(request: InvoiceCreate):
    """Yeni fatura oluşturur ve veritabanına kaydeder."""
    # Müşteri kontrolü
    customer = get_customer(request.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Müşteri bulunamadı: ID {request.customer_id}"
        )
    
    # Malzeme kontrolü
    materials = manager.get_material_names()
    if request.material_name not in materials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Malzeme bulunamadı: '{request.material_name}'"
        )
    
    # Yazıcı kontrolü (opsiyonel)
    if request.printer_id:
        printer = get_printer(request.printer_id)
        if not printer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Yazıcı bulunamadı: ID {request.printer_id}"
            )
    
    # Maliyet hesapla
    time_hours = request.print_time_minutes / 60
    total, details = manager.calculate_cost(
        material_name=request.material_name,
        print_time_hours=time_hours,
        print_weight_g=request.print_weight_grams,
        printer_id=request.printer_id,
        is_first_print=request.is_first_print
    )
    
    # Fatura oluştur ve kaydet
    invoice_data = manager.generate_invoice_data(
        cost_details=details,
        customer_id=request.customer_id,
        printer_id=request.printer_id,
        special_discount=request.special_discount,
        special_discount_note=request.special_discount_note,
        total_cost=total - request.special_discount,
        save_to_db=True
    )
    
    return InvoiceResponse(
        invoice_id=invoice_data.get("invoice_id", 0),
        invoice_number=invoice_data.get("invoice_number", ""),
        date=invoice_data.get("date", ""),
        customer_name=invoice_data.get("customer_name", ""),
        customer_company=invoice_data.get("customer_company"),
        printer_name=invoice_data.get("printer_name"),
        material_name=invoice_data.get("material_name", ""),
        print_weight_g=invoice_data.get("print_weight_g", 0),
        print_time_hours=invoice_data.get("print_time_hours", 0),
        is_first_print=invoice_data.get("is_first_print", True),
        material_cost=invoice_data.get("material_cost", 0),
        energy_cost=invoice_data.get("energy_cost", 0),
        depreciation_cost=invoice_data.get("depreciation_cost", 0),
        preparation_cost=invoice_data.get("preparation_cost", 0),
        failure_risk_cost=invoice_data.get("failure_risk_cost", 0),
        special_discount=invoice_data.get("special_discount", 0),
        special_discount_note=invoice_data.get("special_discount_note", ""),
        total_cost=invoice_data.get("total_cost", 0),
        currency=invoice_data.get("currency", "TRY")
    )


@app.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    tags=["Faturalar"],
    summary="Fatura detayı"
)
async def get_invoice_detail(invoice_id: int):
    """Belirli bir faturanın detaylarını döndürür."""
    inv = get_invoice(invoice_id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fatura bulunamadı: ID {invoice_id}"
        )
    
    # inv: (id, invoice_number, customer_id, printer_id, material_name, 
    #       print_weight_g, print_time_hours, is_first_print, material_cost,
    #       energy_cost, depreciation_cost, preparation_cost, failure_risk_cost,
    #       special_discount, special_discount_note, total_cost, currency, created_at,
    #       customer_name, company, address, phone, email, tax_number, printer_name)
    return InvoiceResponse(
        invoice_id=inv[0],
        invoice_number=inv[1],
        date=inv[17].split(" ")[0] if inv[17] else "",  # created_at'tan tarih
        customer_name=inv[18] or "",
        customer_company=inv[19],
        printer_name=inv[24],
        material_name=inv[4] or "",
        print_weight_g=inv[5] or 0,
        print_time_hours=inv[6] or 0,
        is_first_print=bool(inv[7]),
        material_cost=inv[8] or 0,
        energy_cost=inv[9] or 0,
        depreciation_cost=inv[10] or 0,
        preparation_cost=inv[11] or 0,
        failure_risk_cost=inv[12] or 0,
        special_discount=inv[13] or 0,
        special_discount_note=inv[14] or "",
        total_cost=inv[15] or 0,
        currency=inv[16] or "TRY"
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get(
    "/health",
    tags=["Sistem"],
    summary="Sağlık kontrolü"
)
async def health_check():
    """API sağlık durumunu kontrol eder."""
    return {
        "status": "healthy",
        "service": "3D Yazıcı Maliyet Hesaplayıcı API",
        "version": "2.0.0"
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)