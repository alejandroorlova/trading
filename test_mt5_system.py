#!/usr/bin/env python3
"""
Script de prueba completo del sistema de trading MT5
"""

import requests
import json
import time
from datetime import datetime
from colorama import init, Fore, Style

# Inicializar colorama para colores en consola
init(autoreset=True)

# Configuración
BASE_URL = "http://127.0.0.1:5001"
HEADERS = {"Content-Type": "application/json"}

def print_section(title):
    """Imprimir sección con formato"""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}{title}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

def check_health():
    """Verificar salud del sistema"""
    print_section("1. VERIFICANDO SALUD DEL SISTEMA")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n{Fore.GREEN}✅ Estado general: {data['status']}")
            
            for component, status in data['components'].items():
                if status in ["healthy", "connected", "running"]:
                    print(f"{Fore.GREEN}   ✓ {component}: {status}")
                else:
                    print(f"{Fore.RED}   ✗ {component}: {status}")
            
            return data['components']['mt5'] == 'connected'
        else:
            print(f"{Fore.RED}❌ Error verificando salud: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}❌ No se pudo conectar al servidor")
        print(f"{Fore.YELLOW}   Asegúrate de que el bot esté ejecutándose: python main.py")
        return False

def check_config():
    """Verificar configuración"""
    print_section("2. VERIFICANDO CONFIGURACIÓN")
    
    try:
        response = requests.get(f"{BASE_URL}/config")
        if response.status_code == 200:
            config = response.json()
            
            print(f"\n{Fore.GREEN}📊 Configuración de Trading:")
            print(f"   • Tamaño de posición: {config['trading']['position_size']} lotes")
            print(f"   • Ratios configurados: {config['trading']['reward_ratios']}")
            print(f"   • Alertas por señal: {config['trading']['alerts_per_signal']}")
            
            print(f"\n{Fore.GREEN}⚙️ Gestión de Riesgo:")
            print(f"   • Margen SL: {config['risk_management']['sl_margin_ticks']} ticks")
            print(f"   • Distancia mínima SL: {config['risk_management']['min_sl_distance']} ticks")
            
            print(f"\n{Fore.GREEN}⏱️ Tiempos:")
            print(f"   • Delay de ejecución: {config['timing']['execution_delay_seconds']} segundos")
            print(f"   • Intervalo de verificación: {config['timing']['price_check_interval']} segundos")
            
            return True
        else:
            print(f"{Fore.RED}❌ Error obteniendo configuración")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}")
        return False

def send_test_alert(symbol="EURUSD", action="BUY"):
    """Enviar alerta de prueba"""
    print_section(f"3. ENVIANDO ALERTA DE PRUEBA: {symbol} {action}")
    
    payload = {
        "symbol": symbol,
        "action": action
    }
    
    print(f"\n{Fore.YELLOW}📨 Enviando: {json.dumps(payload)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook/tradingview",
            data=json.dumps(payload),
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data['result']
            
            print(f"\n{Fore.GREEN}✅ Alerta procesada exitosamente!")
            print(f"   • Símbolo: {result['symbol']}")
            print(f"   • Acción: {result['action']}")
            print(f"   • Alertas creadas: {result['alerts_created']}")
            print(f"   • Ratios: {result['ratios_used']}")
            print(f"   • Ejecución programada: {result['execution_time']}")
            
            # Mostrar IDs creados
            print(f"\n{Fore.CYAN}📋 IDs de alertas creadas:")
            for alert in result['alerts']:
                print(f"   • ID {alert['id']}: Ratio 1:{alert['ratio_beneficio']} - {alert['estatus']}")
            
            return result['alerts']
            
        elif response.status_code == 409:
            print(f"{Fore.YELLOW}⚠️ Alerta duplicada (ya existe en este minuto)")
            return None
        else:
            print(f"{Fore.RED}❌ Error: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error enviando alerta: {e}")
        return None

def monitor_execution(alert_ids, duration=70):
    """Monitorear la ejecución de las alertas"""
    print_section("4. MONITOREANDO EJECUCIÓN")
    
    if not alert_ids:
        print(f"{Fore.YELLOW}⚠️ No hay alertas para monitorear")
        return
    
    print(f"\n{Fore.YELLOW}⏰ Esperando {duration} segundos para la ejecución...")
    print(f"{Fore.CYAN}   Las operaciones se ejecutarán al minuto siguiente")
    
    start_time = time.time()
    last_check = 0
    
    while time.time() - start_time < duration:
        elapsed = int(time.time() - start_time)
        
        # Mostrar progreso cada 10 segundos
        if elapsed % 10 == 0 and elapsed != last_check:
            remaining = duration - elapsed
            print(f"{Fore.CYAN}   ⏱️ Tiempo transcurrido: {elapsed}s | Restante: {remaining}s")
            last_check = elapsed
            
            # Verificar estado de las alertas
            try:
                response = requests.get(f"{BASE_URL}/alerts?limit=20")
                if response.status_code == 200:
                    alerts = response.json()['alerts']
                    
                    # Filtrar nuestras alertas
                    our_alerts = [a for a in alerts if a['id'] in [alert['id'] for alert in alert_ids]]
                    
                    # Contar por estado
                    pending = sum(1 for a in our_alerts if a['estatus'] == 'PENDIENTE')
                    open_count = sum(1 for a in our_alerts if a['estatus'] == 'ABIERTA')
                    
                    if open_count > 0:
                        print(f"{Fore.GREEN}   ✅ {open_count} operaciones abiertas!")
                    if pending > 0:
                        print(f"{Fore.YELLOW}   ⏳ {pending} operaciones pendientes")
                        
            except:
                pass
        
        time.sleep(1)
    
    print(f"\n{Fore.GREEN}✅ Monitoreo completado")

def check_results():
    """Verificar resultados y estadísticas"""
    print_section("5. VERIFICANDO RESULTADOS")
    
    try:
        # Obtener estadísticas
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()['stats']
            
            print(f"\n{Fore.GREEN}📊 Estadísticas del Sistema:")
            print(f"   • Total alertas: {stats['total_alerts']}")
            
            print(f"\n{Fore.CYAN}Por Estado:")
            for status, count in stats['by_status'].items():
                print(f"   • {status.upper()}: {count}")
            
            print(f"\n{Fore.CYAN}Por Acción:")
            print(f"   • BUY: {stats['by_action']['buy']}")
            print(f"   • SELL: {stats['by_action']['sell']}")
            
            if stats['performance']['beneficio_total'] != 0:
                print(f"\n{Fore.CYAN}Rendimiento:")
                print(f"   • Beneficio total: ${stats['performance']['beneficio_total']:.2f}")
                print(f"   • Win rate: {stats['performance']['win_rate']}%")
                print(f"   • Ganadas: {stats['performance']['total_wins']}")
                print(f"   • Perdidas: {stats['performance']['total_losses']}")
        
        # Obtener últimas alertas
        response = requests.get(f"{BASE_URL}/alerts?limit=10")
        if response.status_code == 200:
            alerts = response.json()['alerts']
            
            print(f"\n{Fore.CYAN}📋 Últimas 10 Alertas:")
            for alert in alerts[:10]:
                status_color = Fore.GREEN if alert['estatus'] in ['ABIERTA', 'TP'] else Fore.YELLOW
                print(f"{status_color}   • ID {alert['id']}: {alert['symbol']} {alert['action']} | "
                      f"Ratio 1:{alert['ratio_beneficio']} | {alert['estatus']}")
                
                if alert['estatus'] == 'ABIERTA' and alert['stop_loss'] and alert['take_profit']:
                    print(f"     SL: {alert['stop_loss']:.5f} | TP: {alert['take_profit']:.5f}")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error obteniendo resultados: {e}")

def main():
    """Proceso principal de prueba"""
    print(f"{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}🧪 PRUEBA COMPLETA DEL SISTEMA DE TRADING MT5")
    print(f"{Fore.CYAN}{'=' * 60}")
    print(f"\n{Fore.YELLOW}Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Verificar salud
    if not check_health():
        print(f"\n{Fore.RED}❌ El sistema no está saludable. Revisa la configuración.")
        return
    
    # 2. Verificar configuración
    if not check_config():
        return
    
    # 3. Preguntar si enviar alerta de prueba
    print(f"\n{Fore.YELLOW}¿Deseas enviar una alerta de prueba? (s/n): ", end="")
    if input().lower() == 's':
        
        print(f"{Fore.YELLOW}Símbolo [EURUSD]: ", end="")
        symbol = input() or "EURUSD"
        
        print(f"{Fore.YELLOW}Acción (BUY/SELL) [BUY]: ", end="")
        action = input().upper() or "BUY"
        
        # Enviar alerta
        alert_ids = send_test_alert(symbol, action)
        
        if alert_ids:
            # 4. Monitorear ejecución
            print(f"\n{Fore.YELLOW}¿Deseas monitorear la ejecución? (s/n): ", end="")
            if input().lower() == 's':
                monitor_execution(alert_ids)
    
    # 5. Verificar resultados
    check_results()
    
    print(f"\n{Fore.GREEN}{'=' * 60}")
    print(f"{Fore.GREEN}✅ PRUEBA COMPLETADA")
    print(f"{Fore.GREEN}{'=' * 60}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️ Prueba cancelada por el usuario")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error inesperado: {e}")