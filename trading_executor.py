"""
Servicio de ejecución y monitoreo de operaciones de trading
Con recuperación automática de operaciones al reiniciar
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from database import get_db_session
from models import Alert, EstadoOperacion, TipoOperacion
from mt5_service import mt5_service
from config import settings

logger = logging.getLogger(__name__)

class TradingExecutor:
    def __init__(self):
        self.running = False
        self.execution_thread = None
        self.monitoring_thread = None
        
    def start(self):
        """Iniciar el ejecutor y monitor"""
        if self.running:
            logger.warning("⚠️ El ejecutor ya está en funcionamiento")
            return
        
        self.running = True
        
        # Inicializar MT5
        if not mt5_service.initialize():
            logger.error("❌ No se pudo inicializar MT5")
            self.running = False
            return
        
        # IMPORTANTE: Recuperar operaciones abiertas
        self._recover_open_positions()
        
        # Iniciar thread de ejecución de órdenes pendientes
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        
        # Iniciar thread de monitoreo de posiciones abiertas
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("✅ Ejecutor y monitor de trading iniciados")
    
    def _recover_open_positions(self):
        """Recuperar y sincronizar operaciones abiertas tras un reinicio"""
        logger.info("🔄 Recuperando operaciones abiertas...")
        
        with get_db_session() as session:
            # Buscar todas las operaciones marcadas como ABIERTAS en la BD
            open_alerts = session.query(Alert).filter(
                Alert.estatus == EstadoOperacion.ABIERTA,
                Alert.ticket_mt5.isnot(None)
            ).all()
            
            if not open_alerts:
                logger.info("📋 No hay operaciones abiertas para recuperar")
                return
            
            logger.info(f"📊 Encontradas {len(open_alerts)} operaciones marcadas como abiertas")
            
            # Obtener todas las posiciones abiertas en MT5
            import MetaTrader5 as mt5
            mt5_positions = mt5.positions_get()
            mt5_tickets = {pos.ticket: pos for pos in mt5_positions} if mt5_positions else {}
            
            recovered = 0
            closed = 0
            
            for alert in open_alerts:
                try:
                    # Verificar si la operación sigue abierta en MT5
                    if alert.ticket_mt5 in mt5_tickets:
                        # La operación sigue abierta
                        mt5_position = mt5_tickets[alert.ticket_mt5]
                        
                        # Actualizar precio si cambió
                        if alert.price != mt5_position.price_open:
                            alert.price = mt5_position.price_open
                            logger.info(f"   📝 Actualizado precio de Alert {alert.id}")
                        
                        # Verificar que los niveles de SL/TP estén establecidos
                        if not alert.stop_loss or not alert.take_profit:
                            # Recalcular niveles si no están establecidos
                            levels = mt5_service.calculate_sl_tp(
                                alert.symbol, 
                                alert.action, 
                                alert.ratio_beneficio
                            )
                            if levels:
                                alert.stop_loss = levels['stop_loss']
                                alert.take_profit = levels['take_profit']
                                logger.info(f"   📏 Recalculados SL/TP para Alert {alert.id}")
                        
                        logger.info(f"   ✅ Alert {alert.id} (Ticket {alert.ticket_mt5}) sigue abierta")
                        recovered += 1
                        
                    else:
                        # La operación ya no está en MT5 (fue cerrada mientras el bot estaba apagado)
                        logger.warning(f"   ⚠️ Alert {alert.id} (Ticket {alert.ticket_mt5}) ya no está abierta en MT5")
                        
                        # Buscar en el historial para obtener el resultado
                        profit = self._get_historical_profit(alert.ticket_mt5)
                        
                        # Determinar si fue SL o TP basado en el profit y los niveles
                        if profit is not None:
                            alert.beneficio = profit
                            
                            # Intentar determinar si fue SL o TP
                            if profit < 0:
                                alert.estatus = EstadoOperacion.SL
                                logger.info(f"   🔴 Cerrada por SL - Pérdida: ${profit:.2f}")
                            else:
                                alert.estatus = EstadoOperacion.TP
                                logger.info(f"   🟢 Cerrada por TP - Ganancia: ${profit:.2f}")
                        else:
                            # No se pudo determinar, marcar como cerrada genéricamente
                            alert.estatus = EstadoOperacion.SL  # Asumimos SL por seguridad
                            alert.beneficio = 0
                            logger.warning(f"   ❓ No se pudo determinar el resultado")
                        
                        alert.fecha_cierre = datetime.now()
                        closed += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error recuperando Alert {alert.id}: {e}")
            
            session.commit()
            
            logger.info(f"📊 Resumen de recuperación:")
            logger.info(f"   • Operaciones recuperadas (siguen abiertas): {recovered}")
            logger.info(f"   • Operaciones cerradas mientras el bot estaba apagado: {closed}")
            
            # También verificar si hay operaciones en MT5 que no estén en la BD
            self._check_orphan_positions(mt5_tickets, session)
    
    def _check_orphan_positions(self, mt5_tickets: Dict, session):
        """Verificar si hay posiciones en MT5 que no estén registradas en la BD"""
        if not mt5_tickets:
            return
        
        # Obtener todos los tickets de la BD
        db_tickets = session.query(Alert.ticket_mt5).filter(
            Alert.ticket_mt5.isnot(None)
        ).all()
        db_tickets_set = {t[0] for t in db_tickets}
        
        # Buscar posiciones huérfanas
        orphan_tickets = set(mt5_tickets.keys()) - db_tickets_set
        
        if orphan_tickets:
            logger.warning(f"⚠️ Encontradas {len(orphan_tickets)} posiciones en MT5 sin registro en BD")
            
            # Filtrar solo las que tengan nuestro magic number
            our_orphans = []
            for ticket in orphan_tickets:
                position = mt5_tickets[ticket]
                if position.magic == settings.MAGIC_NUMBER:
                    our_orphans.append(position)
                    logger.warning(f"   • Ticket {ticket}: {position.symbol} {position.volume} lotes")
            
            if our_orphans:
                logger.warning("   Estas posiciones pertenecen a este bot pero no tienen registro")
                logger.warning("   Considera cerrarlas manualmente o registrarlas en la BD")
    
    def _get_historical_profit(self, ticket: int) -> float:
        """Obtener el beneficio de una operación cerrada del historial"""
        try:
            import MetaTrader5 as mt5
            
            # Buscar en el historial de deals
            from_date = datetime.now() - timedelta(days=7)  # Buscar en los últimos 7 días
            to_date = datetime.now()
            
            deals = mt5.history_deals_get(from_date, to_date)
            
            if deals:
                for deal in deals:
                    if deal.position_id == ticket:
                        return deal.profit
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo profit histórico para ticket {ticket}: {e}")
            return None
    
    def stop(self):
        """Detener el ejecutor"""
        self.running = False
        
        # Guardar estado antes de cerrar
        self._save_current_state()
        
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        mt5_service.shutdown()
        logger.info("🛑 Ejecutor y monitor detenidos")
    
    def _save_current_state(self):
        """Guardar el estado actual de las operaciones antes de cerrar"""
        logger.info("💾 Guardando estado actual de las operaciones...")
        
        with get_db_session() as session:
            # Actualizar todas las operaciones abiertas con su estado actual
            open_alerts = session.query(Alert).filter(
                Alert.estatus == EstadoOperacion.ABIERTA
            ).all()
            
            if open_alerts:
                logger.info(f"   Guardando estado de {len(open_alerts)} operaciones abiertas")
                session.commit()
    
    def _execution_loop(self):
        """Loop principal para ejecutar órdenes pendientes - Optimizado para cambio de minuto"""
        logger.info("🔄 Loop de ejecución iniciado (sincronizado al minuto)")
        
        while self.running:
            try:
                # Obtener el tiempo actual
                now = datetime.now()
                
                # Buscar alertas pendientes que deban ejecutarse AHORA o antes
                self._process_pending_alerts()
                
                # Calcular cuánto falta para el siguiente segundo
                # Esto permite verificar más frecuentemente cerca del cambio de minuto
                microseconds_to_wait = 1000000 - now.microsecond
                seconds_to_wait = microseconds_to_wait / 1000000.0
                
                # Si estamos cerca del cambio de minuto (últimos 5 segundos), verificar cada 0.5 segundos
                if now.second >= 55:
                    time.sleep(0.5)
                else:
                    # En otros momentos, verificar cada 2 segundos
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error en loop de ejecución: {e}")
                time.sleep(5)
    
    def _monitoring_loop(self):
        """Loop para monitorear posiciones abiertas"""
        logger.info("🔄 Loop de monitoreo iniciado")
        
        while self.running:
            try:
                # Monitorear posiciones abiertas
                self._monitor_open_positions()
                
                # Esperar el intervalo configurado
                time.sleep(settings.PRICE_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"❌ Error en loop de monitoreo: {e}")
                time.sleep(5)
    
    def _process_pending_alerts(self):
        """Procesar alertas pendientes de ejecución"""
        with get_db_session() as session:
            # Obtener alertas pendientes que ya deban ejecutarse
            now = datetime.now()
            
            pending_alerts = session.query(Alert).filter(
                Alert.estatus == EstadoOperacion.PENDIENTE,
                Alert.processed == False,
                Alert.scheduled_execution <= now
            ).all()
            
            if pending_alerts:
                logger.info(f"📋 Procesando {len(pending_alerts)} alertas pendientes")
                
                for alert in pending_alerts:
                    try:
                        # Verificar horario de trading (opcional)
                        current_hour = now.hour
                        if not (settings.TRADING_START_HOUR <= current_hour < settings.TRADING_END_HOUR):
                            logger.warning(f"⏰ Fuera de horario de trading para Alert {alert.id}")
                            continue
                        
                        logger.info(f"🎯 Ejecutando Alert ID={alert.id} | {alert.symbol} {alert.action.value} | Ratio 1:{alert.ratio_beneficio}")
                        
                        # Abrir posición en MT5
                        result = mt5_service.open_position(alert)
                        
                        if result["success"]:
                            # Actualizar alert con los datos de la operación
                            alert.ticket_mt5 = result["ticket"]
                            alert.price = result["price"]
                            alert.stop_loss = result["stop_loss"]
                            alert.take_profit = result["take_profit"]
                            alert.estatus = EstadoOperacion.ABIERTA
                            alert.processed = True
                            alert.opened_at = now
                            alert.magic_number = settings.MAGIC_NUMBER
                            
                            session.commit()
                            
                            logger.info(f"✅ Operación abierta exitosamente:")
                            logger.info(f"   Ticket: {result['ticket']}")
                            logger.info(f"   Precio: {result['price']}")
                            logger.info(f"   SL: {result['stop_loss']} ({result['sl_distance_ticks']:.0f} ticks)")
                            logger.info(f"   TP: {result['take_profit']} ({result['tp_distance_ticks']:.0f} ticks)")
                        else:
                            logger.error(f"❌ Error abriendo posición: {result.get('error')}")
                            # Marcar como procesada para no reintentar infinitamente
                            alert.processed = True
                            alert.estatus = EstadoOperacion.CANCELADA
                            session.commit()
                    
                    except Exception as e:
                        logger.error(f"❌ Error procesando Alert {alert.id}: {e}")
                        alert.processed = True
                        alert.estatus = EstadoOperacion.CANCELADA
                        session.commit()
    
    def _monitor_open_positions(self):
        """Monitorear posiciones abiertas para SL/TP"""
        with get_db_session() as session:
            # Obtener todas las posiciones abiertas
            open_positions = session.query(Alert).filter(
                Alert.estatus == EstadoOperacion.ABIERTA,
                Alert.ticket_mt5.isnot(None)
            ).all()
            
            for alert in open_positions:
                try:
                    # Verificar si el precio ha alcanzado SL o TP
                    level_hit = mt5_service.check_price_levels(alert)
                    
                    if level_hit:
                        logger.info(f"🎯 Nivel {level_hit} alcanzado para Alert {alert.id}")
                        
                        # Cerrar la posición
                        close_result = mt5_service.close_position(
                            alert.ticket_mt5,
                            alert.symbol,
                            alert.action,
                            alert.volume
                        )
                        
                        if close_result["success"]:
                            # Obtener el beneficio real
                            profit = mt5_service.get_position_profit(alert.ticket_mt5)
                            if profit is None:
                                # Calcular beneficio manualmente si no está disponible
                                profit = self._calculate_profit(
                                    alert,
                                    close_result["close_price"]
                                )
                            
                            # Actualizar el registro
                            alert.beneficio = profit
                            alert.estatus = EstadoOperacion.SL if level_hit == 'SL' else EstadoOperacion.TP
                            alert.fecha_cierre = close_result["close_time"]
                            
                            session.commit()
                            
                            # Log del resultado
                            emoji = "🔴" if level_hit == 'SL' else "🟢"
                            logger.info(f"{emoji} Posición cerrada por {level_hit}:")
                            logger.info(f"   Alert ID: {alert.id}")
                            logger.info(f"   Ticket: {alert.ticket_mt5}")
                            logger.info(f"   Símbolo: {alert.symbol}")
                            logger.info(f"   Beneficio: ${profit:.2f}")
                            logger.info(f"   Ratio: 1:{alert.ratio_beneficio}")
                        else:
                            logger.error(f"❌ Error cerrando posición: {close_result.get('error')}")
                    
                except Exception as e:
                    logger.error(f"❌ Error monitoreando Alert {alert.id}: {e}")
    
    def _calculate_profit(self, alert: Alert, close_price: float) -> float:
        """Calcular beneficio manualmente si MT5 no lo proporciona"""
        try:
            # Obtener información del símbolo
            symbol_info = mt5_service.get_symbol_info(alert.symbol)
            if not symbol_info:
                return 0.0
            
            # Calcular la diferencia en puntos
            if alert.action == TipoOperacion.BUY:
                points_diff = close_price - alert.price
            else:  # SELL
                points_diff = alert.price - close_price
            
            # Calcular beneficio
            # Fórmula: (puntos * volumen * valor_del_punto)
            profit = points_diff * alert.volume * symbol_info.trade_contract_size
            
            # Para Forex, ajustar por el tipo de cambio si es necesario
            if symbol_info.profit_currency != "USD":
                # Aquí deberías convertir a USD si es necesario
                pass
            
            return profit
            
        except Exception as e:
            logger.error(f"Error calculando beneficio: {e}")
            return 0.0
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Obtener resumen del estado actual del ejecutor"""
        with get_db_session() as session:
            open_count = session.query(Alert).filter(
                Alert.estatus == EstadoOperacion.ABIERTA
            ).count()
            
            pending_count = session.query(Alert).filter(
                Alert.estatus == EstadoOperacion.PENDIENTE,
                Alert.processed == False
            ).count()
            
            return {
                "executor_running": self.running,
                "mt5_connected": mt5_service.initialized,
                "open_positions": open_count,
                "pending_orders": pending_count,
                "threads_active": {
                    "execution": self.execution_thread.is_alive() if self.execution_thread else False,
                    "monitoring": self.monitoring_thread.is_alive() if self.monitoring_thread else False
                }
            }

# Instancia global
trading_executor = TradingExecutor()