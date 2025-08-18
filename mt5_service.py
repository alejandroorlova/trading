"""
Servicio de MetaTrader 5 para gestión de operaciones de trading
"""

import MetaTrader5 as mt5
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import time

from config import settings
from database import get_db_session
from models import Alert, TipoOperacion, EstadoOperacion

logger = logging.getLogger(__name__)

class MT5Service:
    def __init__(self):
        self.initialized = False
        self.symbol_info_cache = {}
        
    def initialize(self) -> bool:
        """Inicializar conexión con MT5"""
        try:
            # Cerrar cualquier conexión previa
            if self.initialized:
                logger.info("🔄 Cerrando conexión MT5 previa...")
                mt5.shutdown()
                self.initialized = False
                time.sleep(1)
            
            # Inicializar MT5
            logger.info("🔌 Iniciando conexión con MT5...")
            
            if settings.MT5_PATH:
                logger.info(f"   Usando path: {settings.MT5_PATH}")
                if not mt5.initialize(settings.MT5_PATH):
                    error = mt5.last_error()
                    logger.error(f"❌ Error iniciando MT5: {error}")
                    if error[0] == -1:
                        logger.error("   MT5 no encontrado en la ruta especificada")
                    return False
            else:
                if not mt5.initialize():
                    error = mt5.last_error()
                    logger.error(f"❌ Error iniciando MT5: {error}")
                    logger.error("   Posibles causas:")
                    logger.error("   1. MT5 no está instalado")
                    logger.error("   2. MT5 no está en ejecución")
                    logger.error("   3. Necesitas configurar MT5_PATH en .env")
                    return False
            
            logger.info("✅ MT5 inicializado, intentando login...")
            
            # Validar credenciales antes de intentar
            if settings.MT5_LOGIN == 0 or settings.MT5_LOGIN == 123456789:
                logger.error("❌ MT5_LOGIN no configurado correctamente en .env")
                mt5.shutdown()
                return False
            
            if not settings.MT5_PASSWORD:
                logger.error("❌ MT5_PASSWORD no configurado en .env")
                mt5.shutdown()
                return False
            
            if not settings.MT5_SERVER:
                logger.error("❌ MT5_SERVER no configurado en .env")
                mt5.shutdown()
                return False
            
            # Login
            logger.info(f"   Login: {settings.MT5_LOGIN}")
            logger.info(f"   Server: {settings.MT5_SERVER}")
            
            authorized = mt5.login(
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
                server=settings.MT5_SERVER
            )
            
            if not authorized:
                error = mt5.last_error()
                logger.error(f"❌ Error de login en MT5: {error}")
                
                # Mensajes específicos según el error
                if error[0] == -6:
                    logger.error("   Credenciales incorrectas o cuenta inválida")
                    logger.error("   Verifica tu login, password y servidor en .env")
                elif error[0] == -2:
                    logger.error("   Cuenta no válida")
                elif error[0] == -5:
                    logger.error("   No se puede conectar al servidor")
                    logger.error("   Verifica el nombre del servidor y tu conexión a internet")
                
                mt5.shutdown()
                return False
                
            # Obtener info de la cuenta
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"✅ MT5 conectado - Cuenta: {account_info.login}")
                logger.info(f"   Balance: ${account_info.balance:.2f}")
                logger.info(f"   Equity: ${account_info.equity:.2f}")
                logger.info(f"   Servidor: {account_info.server}")
                self.initialized = True
                return True
            else:
                logger.error("❌ No se pudo obtener información de la cuenta")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error inicializando MT5: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Any]:
        """Obtener información del símbolo con caché"""
        if symbol in self.symbol_info_cache:
            return self.symbol_info_cache[symbol]
            
        info = mt5.symbol_info(symbol)
        if info:
            self.symbol_info_cache[symbol] = info
        return info
    
    def get_last_candle_extremes(self, symbol: str) -> Tuple[float, float]:
        """
        Obtener el máximo y mínimo de la vela anterior
        Returns: (high, low)
        """
        try:
            # Obtener las últimas 2 velas (actual y anterior)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 2)
            
            if rates is None or len(rates) < 2:
                logger.error(f"❌ No se pudieron obtener velas para {symbol}")
                return None, None
            
            # La vela anterior es la penúltima (índice -2)
            previous_candle = rates[-2]
            
            high = previous_candle['high']
            low = previous_candle['low']
            
            logger.info(f"📊 Vela anterior de {symbol}: High={high:.5f}, Low={low:.5f}")
            
            return high, low
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo extremos de vela: {e}")
            return None, None
    
    def calculate_sl_tp(self, symbol: str, action: TipoOperacion, ratio: int) -> Dict[str, float]:
        """
        Calcular Stop Loss y Take Profit basado en la vela anterior
        CON PROTECCIÓN CONTRA SPREAD
        """
        try:
            # Obtener información del símbolo
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"❌ No se pudo obtener info del símbolo {symbol}")
                return None
            
            # Obtener precio actual y spread
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                logger.error(f"❌ No se pudo obtener tick para {symbol}")
                return None
            
            current_price = tick.bid
            current_spread = tick.ask - tick.bid
            point = symbol_info.point
            spread_in_ticks = current_spread / point
            
            # Verificar si el spread es demasiado alto
            if settings.SKIP_HIGH_SPREAD and spread_in_ticks > settings.MAX_SPREAD_ALLOWED:
                logger.warning(f"⚠️ Spread muy alto para {symbol}: {spread_in_ticks:.0f} ticks")
                if settings.SKIP_HIGH_SPREAD:
                    return None
            
            
            
            # Obtener extremos de la vela anterior
            high, low = self.get_last_candle_extremes(symbol)
            if high is None or low is None:
                logger.error("❌ No se pudieron obtener extremos de vela")
                return None
            
            # Calcular margen en precio (incluye buffer de spread)
            margin = settings.SL_MARGIN_TICKS * point
            spread_buffer = settings.SPREAD_BUFFER_TICKS * point
            min_distance = settings.MIN_SL_DISTANCE * point
            
            # IMPORTANTE: Añadir buffer adicional basado en el spread actual
            dynamic_buffer = max(spread_buffer, current_spread * 2)  # Al menos 2x el spread
            
            # Calcular Stop Loss según el tipo de operación
            if action == TipoOperacion.BUY:
                # Para compra: SL = mínimo de vela anterior - margen - buffer de spread
                stop_loss = low - margin - dynamic_buffer
                
                # Verificar distancia mínima (incluye spread)
                sl_distance = current_price - stop_loss
                min_required_distance = min_distance + current_spread
                
                if sl_distance < min_required_distance:
                    # Si está muy cerca, usar distancia mínima + spread
                    stop_loss = current_price - min_required_distance
                    sl_distance = min_required_distance
                    logger.warning(f"⚠️ SL ajustado por distancia mínima + spread: {(min_required_distance/point):.0f} ticks")
                
                # Calcular Take Profit basado en ratio
                take_profit = current_price + (sl_distance * ratio)
                
            else:  # SELL
                # Para venta: SL = máximo de vela anterior + margen + buffer de spread
                stop_loss = high + margin + dynamic_buffer
                
                # Verificar distancia mínima (incluye spread)
                sl_distance = stop_loss - current_price
                min_required_distance = min_distance + current_spread
                
                if sl_distance < min_required_distance:
                    # Si está muy cerca, usar distancia mínima + spread
                    stop_loss = current_price + min_required_distance
                    sl_distance = min_required_distance
                    logger.warning(f"⚠️ SL ajustado por distancia mínima + spread: {(min_required_distance/point):.0f} ticks")
                
                # Calcular Take Profit basado en ratio
                take_profit = current_price - (sl_distance * ratio)
            
            # Redondear a los decimales del símbolo
            digits = symbol_info.digits
            stop_loss = round(stop_loss, digits)
            take_profit = round(take_profit, digits)
            
            # Verificar ratio risk/reward real
            actual_risk = abs(current_price - stop_loss)
            actual_reward = abs(take_profit - current_price)
            actual_ratio = actual_reward / actual_risk if actual_risk > 0 else 0
            
            logger.info(f"📈 Niveles calculados para {symbol} {action.value}:")
            logger.info(f"   Precio: {current_price:.{digits}f}")
            logger.info(f"   Spread actual: {spread_in_ticks:.0f} ticks")
            logger.info(f"   SL: {stop_loss:.{digits}f} ({abs(current_price-stop_loss)/point:.0f} ticks)")
            logger.info(f"   TP: {take_profit:.{digits}f} ({abs(take_profit-current_price)/point:.0f} ticks)")
            logger.info(f"   Ratio real: 1:{actual_ratio:.1f} (objetivo 1:{ratio})")
            
            # Advertencia si el ratio real es muy diferente al objetivo
            if actual_ratio < ratio * 0.8:
                logger.warning(f"⚠️ Ratio real ({actual_ratio:.1f}) menor al objetivo ({ratio}) debido al spread")
            
            return {
                'price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'sl_distance_ticks': abs(current_price - stop_loss) / point,
                'tp_distance_ticks': abs(take_profit - current_price) / point,
                'spread_ticks': spread_in_ticks,
                'actual_ratio': actual_ratio
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculando SL/TP: {e}")
            return None
    
    def open_position(self, alert: Alert) -> Dict[str, Any]:
        """Abrir una posición en MT5"""
        try:
            if not self.initialized:
                if not self.initialize():
                    return {"success": False, "error": "No se pudo conectar a MT5"}
            
            symbol = alert.symbol
            
            # Verificar que el símbolo esté disponible
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return {"success": False, "error": f"Símbolo {symbol} no encontrado"}
            
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)
            
            
             # Calcular precio y niveles según configuración
            levels = None
            if settings.USE_SLTP:
                levels = self.calculate_sl_tp(symbol, alert.action, alert.ratio_beneficio)
                if not levels:
                    return {"success": False, "error": "No se pudieron calcular niveles SL/TP"}
                price = levels['price']
            else:
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    return {"success": False, "error": f"No se pudo obtener precio para {symbol}"}
                price = tick.bid

            # Preparar la orden
            order_type = mt5.ORDER_TYPE_BUY if alert.action == TipoOperacion.BUY else mt5.ORDER_TYPE_SELL
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": alert.volume,
                "type": order_type,
                "price": price,
                "deviation": settings.SLIPPAGE,
                "magic": settings.MAGIC_NUMBER,
                "comment": f"Alert_{alert.id}_R{alert.ratio_beneficio}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Enviar orden SIN SL/TP en MT5 (solo los guardamos en BD)
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Error ejecutando orden: {result.retcode} - {result.comment}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg, "retcode": result.retcode}
            
            logger.info(f"✅ Posición abierta: Ticket={result.order} para Alert ID={alert.id}")
            
            return {
                "success": True,
                "ticket": result.order,
                "price": result.price,
                "volume": result.volume,
                "stop_loss": levels['stop_loss'] if levels else None,
                "take_profit": levels['take_profit'] if levels else None,
                "sl_distance_ticks": levels['sl_distance_ticks'] if levels else 0,
                "tp_distance_ticks": levels['tp_distance_ticks'] if levels else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error abriendo posición: {e}")
            return {"success": False, "error": str(e)}
    
    def close_position(self, ticket: int, symbol: str, action: TipoOperacion, volume: float) -> Dict[str, Any]:
        """Cerrar una posición específica"""
        try:
            if not self.initialized:
                if not self.initialize():
                    return {"success": False, "error": "No se pudo conectar a MT5"}
            
            # Obtener precio actual
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                return {"success": False, "error": f"No se pudo obtener precio para {symbol}"}
            
            # Determinar tipo de orden de cierre (inversa a la apertura)
            if action == TipoOperacion.BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": settings.SLIPPAGE,
                "magic": settings.MAGIC_NUMBER,
                "comment": f"Close_{ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Error cerrando posición: {result.retcode} - {result.comment}"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            logger.info(f"✅ Posición cerrada: Ticket={ticket}")
            
            return {
                "success": True,
                "close_price": price,
                "close_time": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Error cerrando posición: {e}")
            return {"success": False, "error": str(e)}
    
    def get_position_profit(self, ticket: int) -> Optional[float]:
        """Obtener el beneficio de una posición por ticket"""
        try:
            positions = mt5.positions_get(ticket=ticket)
            if positions and len(positions) > 0:
                return positions[0].profit
            
            # Si no está abierta, buscar en el historial
            history = mt5.history_deals_get(position=ticket)
            if history and len(history) > 0:
                # Sumar profit de todas las transacciones de esta posición
                total_profit = sum(deal.profit for deal in history)
                return total_profit
                
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo profit para ticket {ticket}: {e}")
            return None
    
    def check_price_levels(self, alert: Alert) -> str:
        """
        Verificar si el precio ha alcanzado SL o TP
        Returns: 'SL', 'TP', o None
        """
        try:
            if not alert.stop_loss or not alert.take_profit:
                logger.warning(f"⚠️ Alert {alert.id} no tiene SL/TP configurados")
                return None
            
            # IMPORTANTE: Asegurar que el símbolo esté disponible y visible
            symbol_info = self.get_symbol_info(alert.symbol)
            if not symbol_info:
                logger.error(f"❌ Símbolo {alert.symbol} no encontrado")
                return None
            
            # Seleccionar el símbolo si no está visible
            if not symbol_info.visible:
                if not mt5.symbol_select(alert.symbol, True):
                    logger.error(f"❌ No se pudo seleccionar símbolo {alert.symbol}")
                    return None
                time.sleep(0.1)  # Pequeña pausa para asegurar selección
            
            # Obtener precio actual (bid) - SIEMPRE usar bid para comparaciones
            tick = mt5.symbol_info_tick(alert.symbol)
            if not tick:
                logger.error(f"❌ No se pudo obtener precio para {alert.symbol}")
                return None
            
            current_price = tick.bid
            
            # Log detallado para debugging
            logger.debug(f"📊 Verificando {alert.symbol}:")
            logger.debug(f"   Precio actual (bid): {current_price:.5f}")
            logger.debug(f"   SL: {alert.stop_loss:.5f}")
            logger.debug(f"   TP: {alert.take_profit:.5f}")
            
            # Para operaciones de COMPRA
            if alert.action == TipoOperacion.BUY:
                # Verificar Stop Loss (precio cae por debajo del SL)
                if current_price <= alert.stop_loss:
                    logger.info(f"🔴 SL alcanzado para {alert.symbol}: {current_price:.5f} <= {alert.stop_loss:.5f}")
                    return 'SL'
                
                # Verificar Take Profit (precio sube por encima del TP)
                if current_price >= alert.take_profit:
                    logger.info(f"🟢 TP alcanzado para {alert.symbol}: {current_price:.5f} >= {alert.take_profit:.5f}")
                    return 'TP'
            
            # Para operaciones de VENTA
            else:  # SELL
                # Verificar Stop Loss (precio sube por encima del SL)
                if current_price >= alert.stop_loss:
                    logger.info(f"🔴 SL alcanzado para {alert.symbol}: {current_price:.5f} >= {alert.stop_loss:.5f}")
                    return 'SL'
                
                # Verificar Take Profit (precio cae por debajo del TP)
                if current_price <= alert.take_profit:
                    logger.info(f"🟢 TP alcanzado para {alert.symbol}: {current_price:.5f} <= {alert.take_profit:.5f}")
                    return 'TP'
            
            return None
            
        except Exception as e:
            logger.error(f"Error verificando niveles de precio para {alert.symbol}: {e}")
            return None
    
    def shutdown(self):
        """Cerrar conexión con MT5"""
        if self.initialized:
            mt5.shutdown()
            self.initialized = False
            logger.info("🔌 Conexión MT5 cerrada")

# Instancia global
mt5_service = MT5Service()