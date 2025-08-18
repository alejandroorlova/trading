# =============================================================================
# webhook_service.py - VERSION CON SINCRONIZACIÓN AL MINUTO
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import and_

from database import get_db_session
from models import Alert, TipoOperacion, EstadoOperacion
from config import settings

logger = logging.getLogger(__name__)

class WebhookService:
    
    def process_tradingview_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesar alerta de TradingView y crear múltiples registros según ratios configurados
        Programa la ejecución para el INICIO del siguiente minuto
        """
        try:
            # 1. Validar que los campos requeridos estén presentes
            if 'symbol' not in data:
                return {
                    "success": False,
                    "error": "Campo 'symbol' es requerido",
                    "example": {"symbol": "XAUUSD", "action": "BUY"},
                    "timestamp": datetime.now().isoformat()
                }
            
            if 'action' not in data:
                return {
                    "success": False,
                    "error": "Campo 'action' es requerido", 
                    "example": {"symbol": "XAUUSD", "action": "BUY"},
                    "timestamp": datetime.now().isoformat()
                }
            
            # 2. Extraer y validar datos
            symbol = data['symbol'].upper().strip()
            action = data['action'].upper().strip()
            
            # Validar que symbol no esté vacío
            if not symbol:
                return {
                    "success": False,
                    "error": "Campo 'symbol' no puede estar vacío",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Validar action
            if action not in ['BUY', 'SELL']:
                return {
                    "success": False,
                    "error": f"Action '{action}' no válida. Solo se acepta 'BUY' o 'SELL'",
                    "received_action": action,
                    "valid_actions": ["BUY", "SELL"],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 3. Generar clave de minuto para control de duplicados
            now = datetime.now()
            alert_minute = now.strftime("%Y-%m-%d %H:%M")
            
            # IMPORTANTE: Calcular el tiempo de ejecución al INICIO del siguiente minuto
            # Por ejemplo, si son las 14:35:45, ejecutar a las 14:36:00
            current_second = now.second
            current_microsecond = now.microsecond
            
            # Calcular segundos hasta el siguiente minuto
            seconds_to_next_minute = 60 - current_second
            
            # Si estamos muy cerca del cambio de minuto (menos de 2 segundos), esperar al siguiente
            if seconds_to_next_minute < 2:
                seconds_to_next_minute += 60
            
            # Crear datetime exacto del siguiente minuto (00 segundos)
            execution_time = now + timedelta(seconds=seconds_to_next_minute)
            execution_time = execution_time.replace(second=0, microsecond=0)
            
            logger.info(f"📨 Alerta recibida: {symbol} {action} en minuto {alert_minute}")
            logger.info(f"⏰ Hora actual: {now.strftime('%H:%M:%S.%f')[:-3]}")
            logger.info(f"⏰ Programada para: {execution_time.strftime('%H:%M:%S')} (en {seconds_to_next_minute} segundos)")
            
            # 4. Obtener ratios de beneficio configurados
            reward_ratios = settings.get_reward_ratios
            logger.info(f"📊 Ratios configurados: {reward_ratios}")
            
            # 5. Verificar duplicados en base de datos
            with get_db_session() as session:
                
                # Verificar si ya existe alguna alerta para este símbolo en este minuto
                existing_alert = session.query(Alert).filter(
                    and_(
                        Alert.symbol == symbol,
                        Alert.alert_minute == alert_minute
                    )
                ).first()
                
                # Si ya existe, ignorar
                if existing_alert:
                    logger.warning(f"🚫 DUPLICADO: {symbol} ya procesado en {alert_minute}")
                    return {
                        "success": False,
                        "ignored": True,
                        "reason": "duplicate_in_minute",
                        "existing_alert": {
                            "id": existing_alert.id,
                            "symbol": existing_alert.symbol,
                            "action": existing_alert.action.value,
                            "alert_minute": existing_alert.alert_minute
                        },
                        "message": f"Alerta duplicada: {symbol} ya fue procesado en {alert_minute}",
                        "timestamp": now.isoformat()
                    }
                
                # 6. Crear múltiples alertas según los ratios configurados
                created_alerts = []
                tipo_operacion = TipoOperacion.BUY if action == 'BUY' else TipoOperacion.SELL
                
                for ratio in reward_ratios:
                    new_alert = Alert(
                        symbol=symbol,
                        action=tipo_operacion,
                        price=None,  # Se establecerá al abrir la operación
                        volume=settings.POSITION_SIZE,
                        ratio_beneficio=ratio,
                        estatus=EstadoOperacion.PENDIENTE,
                        beneficio=0.0,
                        processed=False,  # No procesada aún
                        scheduled_execution=execution_time,  # Programar para el inicio del siguiente minuto
                        alert_minute=alert_minute,
                        received_at=now,
                        magic_number=settings.MAGIC_NUMBER
                    )
                    
                    session.add(new_alert)
                    session.flush()  # Para obtener el ID
                    
                    created_alerts.append({
                        "id": new_alert.id,
                        "symbol": new_alert.symbol,
                        "action": new_alert.action.value,
                        "ratio_beneficio": new_alert.ratio_beneficio,
                        "estatus": new_alert.estatus.value,
                        "scheduled_execution": new_alert.scheduled_execution.isoformat()
                    })
                    
                    logger.info(f"✅ Alerta creada: ID={new_alert.id} | {symbol} {action} | Ratio 1:{ratio}")
                
                # Confirmar todos los cambios
                session.commit()
                
                logger.info(f"🎯 Total de {len(created_alerts)} alertas creadas para {symbol} {action}")
                logger.info(f"⏰ Todas programadas para ejecutarse exactamente a las {execution_time.strftime('%H:%M:%S')}")
                
                return {
                    "success": True,
                    "symbol": symbol,
                    "action": action,
                    "alert_minute": alert_minute,
                    "alerts_created": len(created_alerts),
                    "ratios_used": reward_ratios,
                    "current_time": now.isoformat(),
                    "execution_time": execution_time.isoformat(),
                    "seconds_to_execution": seconds_to_next_minute,
                    "message": f"Se crearon {len(created_alerts)} alertas para {symbol} {action} - Ejecución al inicio del siguiente minuto",
                    "alerts": created_alerts,
                    "timestamp": now.isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Error procesando alerta: {e}")
            return {
                "success": False,
                "error": f"Error interno del servidor: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_recent_alerts(self, limit: int = 50) -> Dict[str, Any]:
        """Obtener alertas recientes"""
        try:
            with get_db_session() as session:
                alerts = session.query(Alert)\
                    .order_by(Alert.received_at.desc())\
                    .limit(limit)\
                    .all()
                
                return {
                    "success": True,
                    "total": len(alerts),
                    "alerts": [alert.to_dict() for alert in alerts]
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas mejoradas"""
        try:
            with get_db_session() as session:
                total_alerts = session.query(Alert).count()
                
                buy_alerts = session.query(Alert)\
                    .filter(Alert.action == TipoOperacion.BUY)\
                    .count()
                
                sell_alerts = session.query(Alert)\
                    .filter(Alert.action == TipoOperacion.SELL)\
                    .count()
                
                # Estadísticas por estado
                pendientes = session.query(Alert)\
                    .filter(Alert.estatus == EstadoOperacion.PENDIENTE)\
                    .count()
                
                abiertas = session.query(Alert)\
                    .filter(Alert.estatus == EstadoOperacion.ABIERTA)\
                    .count()
                
                cerradas_sl = session.query(Alert)\
                    .filter(Alert.estatus == EstadoOperacion.SL)\
                    .count()
                
                cerradas_tp = session.query(Alert)\
                    .filter(Alert.estatus == EstadoOperacion.TP)\
                    .count()
                
                canceladas = session.query(Alert)\
                    .filter(Alert.estatus == EstadoOperacion.CANCELADA)\
                    .count()
                
                # Estadísticas por ratio
                from sqlalchemy import func
                ratio_stats = session.query(
                    Alert.ratio_beneficio, 
                    func.count(Alert.id).label('count'),
                    func.sum(Alert.beneficio).label('total_profit')
                ).group_by(Alert.ratio_beneficio).all()
                
                # Contar alertas por símbolo
                symbol_stats = session.query(
                    Alert.symbol, 
                    func.count(Alert.id).label('count'),
                    func.sum(Alert.beneficio).label('total_profit')
                ).group_by(Alert.symbol).all()
                
                # Calcular beneficio total
                beneficio_total = session.query(func.sum(Alert.beneficio)).scalar() or 0.0
                
                # Calcular win rate
                total_cerradas = cerradas_sl + cerradas_tp
                win_rate = (cerradas_tp / total_cerradas * 100) if total_cerradas > 0 else 0
                
                return {
                    "success": True,
                    "stats": {
                        "total_alerts": total_alerts,
                        "by_action": {
                            "buy": buy_alerts,
                            "sell": sell_alerts
                        },
                        "by_status": {
                            "pendiente": pendientes,
                            "abierta": abiertas,
                            "sl": cerradas_sl,
                            "tp": cerradas_tp,
                            "cancelada": canceladas
                        },
                        "by_ratio": {
                            ratio: {
                                "count": count,
                                "profit": float(profit or 0)
                            } for ratio, count, profit in ratio_stats
                        },
                        "by_symbol": {
                            symbol: {
                                "count": count,
                                "profit": float(profit or 0)
                            } for symbol, count, profit in symbol_stats
                        },
                        "performance": {
                            "beneficio_total": beneficio_total,
                            "win_rate": round(win_rate, 2),
                            "total_wins": cerradas_tp,
                            "total_losses": cerradas_sl
                        },
                        "config": {
                            "ratios_configurados": settings.get_reward_ratios
                        },
                        "last_updated": datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_alerts_by_status(self, status: str) -> Dict[str, Any]:
        """Obtener alertas por estado"""
        try:
            # Validar estado
            status_upper = status.upper()
            valid_statuses = ['PENDIENTE', 'ABIERTA', 'SL', 'TP', 'CANCELADA']
            
            if status_upper not in valid_statuses:
                return {
                    "success": False,
                    "error": f"Estado '{status}' no válido",
                    "valid_statuses": valid_statuses
                }
            
            with get_db_session() as session:
                estado_enum = EstadoOperacion[status_upper]
                alerts = session.query(Alert)\
                    .filter(Alert.estatus == estado_enum)\
                    .order_by(Alert.received_at.desc())\
                    .all()
                
                return {
                    "success": True,
                    "status": status_upper,
                    "total": len(alerts),
                    "alerts": [alert.to_dict() for alert in alerts]
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo alertas por estado: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Instancia global
webhook_service = WebhookService()