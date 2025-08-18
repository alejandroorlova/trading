#!/usr/bin/env python3
"""
Script de configuración inicial del Bot de Trading MT5
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🤖 CONFIGURACIÓN BOT TRADING MT5")
    print("=" * 60)

def check_python_version():
    """Verificar versión de Python"""
    print("\n📌 Verificando versión de Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        print(f"   Tu versión: Python {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    return True

def install_dependencies():
    """Instalar dependencias"""
    print("\n📦 Instalando dependencias...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def setup_env_file():
    """Configurar archivo .env"""
    print("\n⚙️ Configurando archivo .env...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        response = input("   El archivo .env ya existe. ¿Deseas sobrescribirlo? (s/n): ")
        if response.lower() != 's':
            print("   ⏭️ Manteniendo archivo .env existente")
            return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Archivo .env creado desde .env.example")
        print("\n⚠️ IMPORTANTE: Edita el archivo .env con tus credenciales de MT5:")
        print("   - MT5_LOGIN: Tu número de cuenta")
        print("   - MT5_PASSWORD: Tu contraseña")
        print("   - MT5_SERVER: El servidor de tu broker")
        return True
    else:
        print("❌ No se encontró .env.example")
        return False

def test_mt5_connection():
    """Probar conexión con MT5"""
    print("\n🔌 Probando conexión con MT5...")
    
    try:
        import MetaTrader5 as mt5
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Intentar inicializar MT5
        if not mt5.initialize():
            print("⚠️ No se pudo inicializar MT5")
            print("   Asegúrate de que MetaTrader 5 esté instalado")
            print("   Si usas MT5 portable, configura MT5_PATH en .env")
            return False
        
        # Verificar credenciales
        login = os.getenv("MT5_LOGIN", "0")
        if login == "0" or login == "123456789":
            print("⚠️ No has configurado tus credenciales de MT5 en .env")
            print("   Por favor, edita el archivo .env con tus datos reales")
            mt5.shutdown()
            return False
        
        mt5.shutdown()
        print("✅ MT5 detectado correctamente")
        return True
        
    except ImportError:
        print("❌ No se pudo importar MetaTrader5")
        return False
    except Exception as e:
        print(f"❌ Error probando MT5: {e}")
        return False

def create_database():
    """Crear base de datos inicial"""
    print("\n💾 Creando base de datos...")
    
    try:
        from database import create_tables
        create_tables()
        print("✅ Base de datos creada correctamente")
        return True
    except Exception as e:
        print(f"❌ Error creando base de datos: {e}")
        return False

def print_next_steps():
    """Mostrar siguientes pasos"""
    print("\n" + "=" * 60)
    print("📋 SIGUIENTES PASOS:")
    print("=" * 60)
    print("\n1. Edita el archivo .env con tus credenciales de MT5")
    print("\n2. Asegúrate de que MetaTrader 5 esté instalado y funcionando")
    print("\n3. Ejecuta el bot con:")
    print("   python main.py")
    print("\n4. Configura tu alerta en TradingView para enviar webhooks a:")
    print("   http://tu-servidor:5001/webhook/tradingview")
    print("\n5. El formato del webhook debe ser:")
    print('   {"symbol": "XAUUSD", "action": "BUY"}')
    print("\n" + "=" * 60)

def main():
    """Proceso principal de configuración"""
    print_header()
    
    # Lista de verificaciones
    checks = [
        ("Python", check_python_version),
        ("Dependencias", install_dependencies),
        ("Archivo .env", setup_env_file),
        ("Base de datos", create_database),
        ("MetaTrader 5", test_mt5_connection)
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE CONFIGURACIÓN:")
    print("=" * 60)
    
    all_ok = True
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if not result:
            all_ok = False
    
    if all_ok:
        print("\n🎉 ¡Configuración completada exitosamente!")
        print_next_steps()
    else:
        print("\n⚠️ Algunos componentes requieren atención")
        print("   Revisa los errores anteriores y vuelve a ejecutar setup.py")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Configuración cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")