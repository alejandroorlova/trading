#!/usr/bin/env python3
"""
Script de diagnóstico y prueba de conexión con MetaTrader 5
"""

import MetaTrader5 as mt5
import os
import time
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

def print_section(title):
    print("\n" + "=" * 60)
    print(f"📌 {title}")
    print("=" * 60)

def test_mt5_basic():
    """Prueba básica de MT5"""
    print_section("PRUEBA BÁSICA DE MT5")
    
    # 1. Verificar si MT5 está instalado
    print("\n1. Verificando instalación de MT5...")
    
    # Intentar inicializar sin login
    if mt5.initialize():
        print("✅ MT5 inicializado correctamente")
        
        # Obtener información del terminal de forma segura
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info:
                print(f"\n📊 Información del Terminal:")
                # Listar todos los atributos disponibles
                for attr in dir(terminal_info):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(terminal_info, attr)
                            if not callable(value):
                                print(f"   {attr}: {value}")
                        except:
                            pass
            
            # Obtener versión de forma alternativa
            version_info = mt5.version()
            if version_info:
                print(f"\n📱 Versión de MT5:")
                print(f"   Build: {version_info[0]}")
                print(f"   Fecha: {version_info[1]}")
                
        except Exception as e:
            print(f"⚠️ No se pudo obtener toda la información: {e}")
        
        mt5.shutdown()
        return True
    else:
        error = mt5.last_error()
        print(f"❌ No se pudo inicializar MT5: {error}")
        print("\nPosibles causas:")
        print("  1. MetaTrader 5 no está instalado")
        print("  2. MT5 no está en ejecución")
        print("  3. Necesitas especificar MT5_PATH en .env")
        return False

def test_mt5_login():
    """Prueba de login en MT5"""
    print_section("PRUEBA DE LOGIN EN MT5")
    
    # Obtener credenciales
    login = os.getenv("MT5_LOGIN", "0")
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")
    mt5_path = os.getenv("MT5_PATH", "")
    
    print(f"\nCredenciales configuradas:")
    print(f"  Login: {login}")
    print(f"  Password: {'*' * len(password) if password else '(vacío)'}")
    print(f"  Server: {server}")
    print(f"  MT5 Path: {mt5_path if mt5_path else '(default)'}")
    
    # Validar credenciales
    if login == "0" or login == "123456789":
        print("\n❌ No has configurado tu login real en .env")
        print("   El login debe ser tu número de cuenta de MT5")
        return False
    
    if not password:
        print("\n❌ No has configurado tu password en .env")
        return False
    
    if not server:
        print("\n❌ No has configurado el servidor en .env")
        print("\n📋 Para encontrar tu servidor:")
        print("   1. Abre MetaTrader 5")
        print("   2. Ve a Archivo > Conectar a cuenta de trading")
        print("   3. Copia el nombre exacto del servidor")
        return False
    
    print("\n2. Intentando inicializar MT5...")
    
    # Cerrar cualquier conexión previa
    mt5.shutdown()
    time.sleep(1)
    
    # Intentar inicializar con path si está configurado
    if mt5_path:
        print(f"   Usando path personalizado: {mt5_path}")
        init_result = mt5.initialize(mt5_path)
    else:
        print("   Usando MT5 por defecto del sistema")
        init_result = mt5.initialize()
    
    if not init_result:
        error = mt5.last_error()
        print(f"❌ No se pudo inicializar MT5: {error}")
        return False
    
    print("✅ MT5 inicializado")
    
    print("\n3. Intentando login...")
    print(f"   Login: {login}")
    print(f"   Server: {server}")
    
    # Convertir login a entero
    try:
        login_int = int(login)
    except ValueError:
        print(f"❌ El login debe ser numérico, recibido: {login}")
        mt5.shutdown()
        return False
    
    # Intentar login
    authorized = mt5.login(
        login=login_int,
        password=password,
        server=server,
        timeout=10000  # 10 segundos de timeout
    )
    
    if authorized:
        print("✅ Login exitoso!")
        
        # Obtener información de la cuenta
        account_info = mt5.account_info()
        if account_info:
            print(f"\n📊 Información de la cuenta:")
            print(f"   Cuenta: {account_info.login}")
            print(f"   Servidor: {account_info.server}")
            print(f"   Balance: ${account_info.balance:.2f}")
            print(f"   Equity: ${account_info.equity:.2f}")
            print(f"   Margen libre: ${account_info.margin_free:.2f}")
            print(f"   Apalancamiento: 1:{account_info.leverage}")
            print(f"   Moneda: {account_info.currency}")
            print(f"   Compañía: {account_info.company}")
        
        # Verificar símbolos disponibles
        print(f"\n📈 Verificando símbolos disponibles...")
        symbols_to_check = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
        available_symbols = []
        
        for symbol in symbols_to_check:
            info = mt5.symbol_info(symbol)
            if info and info.visible:
                print(f"   ✅ {symbol} disponible")
                available_symbols.append(symbol)
            else:
                print(f"   ❌ {symbol} no disponible")
        
        # Si no hay símbolos comunes, mostrar algunos disponibles
        if not available_symbols:
            print("\n📋 Buscando símbolos disponibles en tu broker...")
            all_symbols = mt5.symbols_get()
            if all_symbols:
                print(f"   Total de símbolos: {len(all_symbols)}")
                print("   Primeros 10 símbolos disponibles:")
                for i, symbol in enumerate(all_symbols[:10]):
                    print(f"      {i+1}. {symbol.name}")
        
        mt5.shutdown()
        return True
    else:
        error = mt5.last_error()
        print(f"\n❌ Login fallido: {error}")
        
        print("\n🔍 Diagnóstico del error:")
        
        if error[0] == -6:
            print("   📌 Error: Authorization failed")
            print("   Causas posibles:")
            print("      1. Usuario o contraseña incorrectos")
            print("      2. Nombre del servidor incorrecto")
            print("      3. Cuenta desactivada o expirada")
            print("\n   Solución:")
            print("      1. Verifica que puedas hacer login manualmente en MT5")
            print("      2. Copia exactamente el nombre del servidor")
            print("      3. Asegúrate de usar la contraseña correcta")
            
        elif error[0] == -2:
            print("   📌 Error: Invalid account")
            print("   La cuenta especificada no es válida")
            
        elif error[0] == -5:
            print("   📌 Error: Connection failed")
            print("   No se puede conectar al servidor")
            print("   Verifica tu conexión a internet y el nombre del servidor")
            
        elif error[0] == -4:
            print("   📌 Error: Connection timeout")
            print("   El servidor no responde")
            print("   Puede ser un problema temporal o firewall")
        
        else:
            print(f"   📌 Código de error: {error[0]}")
            print(f"   Mensaje: {error[1]}")
        
        mt5.shutdown()
        return False

def list_available_servers():
    """Listar servidores disponibles"""
    print_section("SERVIDORES DISPONIBLES")
    
    print("\n🌐 Servidores demo comunes:")
    servers = [
        "MetaQuotes-Demo",
        "ICMarkets-Demo",
        "ICMarketsSC-Demo",
        "XMGlobal-Demo",
        "XMGlobal-MT5 3",
        "Pepperstone-Demo",
        "Pepperstone-MT5",
        "FBS-Demo",
        "RoboForex-Demo",
        "Exness-Trial",
        "OctaFX-Demo",
        "Alpari-Demo"
    ]
    
    for server in servers:
        print(f"   • {server}")
    
    print("\n💡 Nota: El nombre debe ser EXACTO como aparece en MT5")

def fix_mt5_state():
    """Intentar arreglar el estado de MT5"""
    print_section("REINICIO DE MT5")
    
    print("\n1. Cerrando conexiones previas...")
    try:
        mt5.shutdown()
        time.sleep(1)
        print("✅ Conexiones cerradas")
    except:
        pass
    
    print("\n2. Esperando 2 segundos...")
    time.sleep(2)
    
    print("\n3. Reiniciando MT5...")
    if mt5.initialize():
        print("✅ MT5 reiniciado correctamente")
        mt5.shutdown()
        return True
    else:
        print("❌ No se pudo reiniciar MT5")
        print("   Intenta abrir MetaTrader 5 manualmente")
        return False

def show_env_template():
    """Mostrar plantilla de .env correcta"""
    print_section("PLANTILLA DE CONFIGURACIÓN (.env)")
    
    print("""
# ===================================
# METATRADER 5 - CONFIGURACIÓN
# ===================================

# Tu número de cuenta (sin comillas ni espacios)
MT5_LOGIN=12345678

# Tu contraseña (sin comillas)
MT5_PASSWORD=tupassword

# Nombre EXACTO del servidor (sensible a mayúsculas/minúsculas)
MT5_SERVER=MetaQuotes-Demo

# Opcional: Solo si MT5 no se detecta automáticamente
# MT5_PATH=C:/Program Files/MetaTrader 5/terminal64.exe

# ===================================
# CONFIGURACIÓN DE TRADING
# ===================================
POSITION_SIZE=0.01
MAGIC_NUMBER=123456
SLIPPAGE=10
REWARD_RATIOS=2,3,4,5,6,7,8,9
SL_MARGIN_TICKS=5
MIN_SL_DISTANCE=20
EXECUTION_DELAY_SECONDS=60
PRICE_CHECK_INTERVAL=1
""")

def main():
    print("=" * 60)
    print("🔧 DIAGNÓSTICO DE CONEXIÓN MT5")
    print("=" * 60)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Prueba básica
        if not test_mt5_basic():
            print("\n⚠️ MT5 no está disponible en el sistema")
            print("\nSoluciones:")
            print("1. Descarga e instala MetaTrader 5 desde:")
            print("   https://www.metatrader5.com/")
            print("2. Si ya está instalado, ábrelo manualmente")
            print("3. Si usas instalación portable, configura MT5_PATH en .env")
            return
        
        # 2. Limpiar estado
        fix_mt5_state()
        
        # 3. Prueba de login
        if not test_mt5_login():
            print("\n" + "=" * 60)
            print("❌ FALLO EN LA AUTENTICACIÓN")
            print("=" * 60)
            
            list_available_servers()
            show_env_template()
            
            print("\n📋 PASOS PARA SOLUCIONAR:")
            print("1. Abre MetaTrader 5 manualmente")
            print("2. Haz login con tus credenciales para verificar que funcionan")
            print("3. En MT5: Archivo > Conectar a cuenta de trading")
            print("4. Copia el nombre EXACTO del servidor")
            print("5. Actualiza el archivo .env con los datos correctos")
            print("6. Ejecuta este script nuevamente")
        else:
            print("\n" + "=" * 60)
            print("🎉 ¡CONEXIÓN EXITOSA!")
            print("=" * 60)
            print("\nTu configuración de MT5 está correcta.")
            print("Ahora puedes ejecutar: python main.py")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProceso cancelado")
    finally:
        try:
            mt5.shutdown()
        except:
            pass