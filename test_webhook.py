#!/usr/bin/env python3
"""
Script de prueba para webhook.biovivecare.com
"""

import requests
import json
import time
from datetime import datetime

# URLs
LOCAL_URL = "http://127.0.0.1:5000"
CLOUDFLARE_URL = "https://webhook.biovivecare.com"

def print_section(title):
    print("\n" + "=" * 60)
    print(f"📌 {title}")
    print("=" * 60)

def test_local_connection():
    """Verificar que el bot esté ejecutándose localmente"""
    print_section("PRUEBA LOCAL")
    
    try:
        print(f"🔍 Probando: {LOCAL_URL}/health")
        response = requests.get(f"{LOCAL_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bot ejecutándose localmente")
            print(f"   Estado: {data['status']}")
            print(f"   Componentes: {data['components']}")
            return True
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ No se puede conectar al bot localmente")
        print(f"   Asegúrate de ejecutar: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cloudflare_connection():
    """Verificar conexión a través de Cloudflare"""
    print_section("PRUEBA CLOUDFLARE")
    
    try:
        print(f"☁️ Probando: {CLOUDFLARE_URL}/health")
        
        response = requests.get(
            f"{CLOUDFLARE_URL}/health",
            timeout=15,
            headers={
                "User-Agent": "TradingBot-Test/1.0",
                "Accept": "application/json"
            },
            verify=True  # Verificar certificado SSL
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cloudflare Tunnel funcionando correctamente")
            print(f"   Estado: {data['status']}")
            
            # Mostrar headers de Cloudflare
            if "cf-ray" in response.headers:
                print(f"   CF-Ray ID: {response.headers['cf-ray']}")
            if "server" in response.headers:
                print(f"   Server: {response.headers['server']}")
                
            return True
            
        elif response.status_code == 404:
            print(f"❌ Error 404: El túnel no está encontrando el servicio")
            print(f"   Verifica que el puerto en config.yml sea 5001")
            return False
            
        else:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"❌ Error SSL/TLS:")
        print(f"   {str(e)[:200]}")
        print(f"\n📋 Soluciones:")
        print(f"   1. Verifica que el túnel esté activo")
        print(f"   2. Revisa la configuración SSL en Cloudflare Dashboard")
        return False
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: La conexión tardó demasiado")
        print(f"   El túnel puede estar sobrecargado o inactivo")
        return False
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_webhook_local():
    """Probar webhook localmente"""
    print_section("PRUEBA WEBHOOK LOCAL")
    
    payload = {
        "symbol": "EURUSD",
        "action": "BUY"
    }
    
    try:
        print(f"📨 Enviando alerta de prueba local...")
        print(f"   Payload: {json.dumps(payload)}")
        
        response = requests.post(
            f"{LOCAL_URL}/webhook/tradingview",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook local funcionando")
            print(f"   Mensaje: {result.get('message')}")
            print(f"   Alertas creadas: {result['result']['alerts_created']}")
            return True
            
        elif response.status_code == 409:
            print(f"⚠️ Alerta duplicada (webhook funciona correctamente)")
            return True
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_webhook_cloudflare():
    """Probar webhook a través de Cloudflare"""
    print_section("PRUEBA WEBHOOK CLOUDFLARE")
    
    payload = {
        "symbol": "GBPUSD",
        "action": "SELL"
    }
    
    webhook_url = f"{CLOUDFLARE_URL}/webhook/tradingview"
    
    try:
        print(f"☁️ Enviando alerta a través de Cloudflare...")
        print(f"   URL: {webhook_url}")
        print(f"   Payload: {json.dumps(payload)}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "TradingView"  # Simular TradingView
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook Cloudflare funcionando perfectamente")
            print(f"   Mensaje: {result.get('message')}")
            print(f"   Alertas creadas: {result['result']['alerts_created']}")
            
            print(f"\n🎉 ¡ÉXITO! Puedes usar esta URL en TradingView:")
            print(f"   {webhook_url}")
            return True
            
        elif response.status_code == 409:
            print(f"⚠️ Alerta duplicada (webhook funciona correctamente)")
            print(f"\n✅ El webhook está funcionando. URL para TradingView:")
            print(f"   {webhook_url}")
            return True
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_tradingview_setup():
    """Mostrar instrucciones para TradingView"""
    print_section("CONFIGURACIÓN EN TRADINGVIEW")
    
    print("""
📋 Cómo configurar en TradingView:

1. En tu gráfico de TradingView, crea o edita tu alerta

2. En la sección "Notificaciones", activa "Webhook URL"

3. Ingresa esta URL:
   https://webhook.biovivecare.com/webhook/tradingview

4. En el campo "Mensaje", usa este formato JSON:
   {
     "symbol": "{{ticker}}",
     "action": "BUY"
   }
   
   O para venta:
   {
     "symbol": "{{ticker}}",
     "action": "SELL"
   }

5. Guarda la alerta

⚠️ IMPORTANTE:
   - Usa comillas dobles en el JSON
   - {{ticker}} es una variable de TradingView
   - Cambia BUY/SELL según tu estrategia
""")

def main():
    print("=" * 60)
    print("🔧 PRUEBA DE WEBHOOK - BIOVIVECARE")
    print("=" * 60)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nDominio: webhook.biovivecare.com")
    print(f"Puerto local: 5001")
    
    # Ejecutar pruebas
    tests = []
    
    # 1. Prueba local
    local_ok = test_local_connection()
    tests.append(("Conexión Local", local_ok))
    
    if not local_ok:
        print("\n❌ El bot no está ejecutándose")
        print("   Ejecuta en otra terminal: python main.py")
        return
    
    time.sleep(1)
    
    # 2. Prueba Cloudflare
    cf_ok = test_cloudflare_connection()
    tests.append(("Conexión Cloudflare", cf_ok))
    
    time.sleep(1)
    
    # 3. Prueba webhook local
    webhook_local_ok = test_webhook_local()
    tests.append(("Webhook Local", webhook_local_ok))
    
    time.sleep(2)  # Esperar más para evitar duplicados
    
    # 4. Prueba webhook Cloudflare
    if cf_ok:
        webhook_cf_ok = test_webhook_cloudflare()
        tests.append(("Webhook Cloudflare", webhook_cf_ok))
    else:
        print("\n⏭️ Saltando prueba de webhook Cloudflare (túnel no conectado)")
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    all_passed = True
    for name, result in tests:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ¡TODO FUNCIONANDO CORRECTAMENTE!")
        show_tradingview_setup()
    else:
        print("\n📋 PASOS PARA SOLUCIONAR:")
        
        if not tests[0][1]:  # Local no funciona
            print("1. Ejecuta el bot: python main.py")
            
        elif not tests[1][1]:  # Cloudflare no funciona
            print("1. Verifica que config.yml tenga el puerto 5001")
            print("2. Reinicia el túnel de Cloudflare")
            print("3. Comando: cloudflared tunnel --config C:\\Users\\alexv\\.cloudflared\\config.yml run tradingview-mt5")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrueba cancelada")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")