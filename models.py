from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

class TipoOperacion(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class EstadoOperacion(enum.Enum):
    PENDIENTE = "PENDIENTE"  # Esperando apertura
    ABIERTA = "ABIERTA"      # Operación abierta en MT5
    SL = "SL"                # Cerrada por Stop Loss
    TP = "TP"                # Cerrada por Take Profit
    CANCELADA = "CANCELADA"  # Cancelada manualmente

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Datos de la alerta
    symbol = Column(String(10), nullable=False)          # EURUSD, XAUUSD
    action = Column(Enum(TipoOperacion), nullable=False)  # BUY/SELL
    price = Column(Float, nullable=True)                 # Precio de entrada real
    volume = Column(Float, nullable=False, default=0.01) # Volumen
    
    # Niveles de trading
    stop_loss = Column(Float, nullable=True)             # Nivel de Stop Loss calculado
    take_profit = Column(Float, nullable=True)           # Nivel de Take Profit calculado
    
    # Estado y resultados
    estatus = Column(Enum(EstadoOperacion), nullable=False, default=EstadoOperacion.PENDIENTE)
    beneficio = Column(Float, nullable=True, default=0.0)  # Beneficio/Pérdida en $
    ratio_beneficio = Column(Integer, nullable=False)      # Ratio de beneficio (2, 3, 4, etc.)
    
    # MetaTrader 5
    ticket_mt5 = Column(Integer, nullable=True)            # ID de la operación en MT5
    magic_number = Column(Integer, nullable=True)          # Magic number para identificación
    
    # Control de procesamiento
    processed = Column(Boolean, nullable=False, default=False)  # Si ya fue procesada para apertura
    scheduled_execution = Column(DateTime, nullable=True)       # Cuándo debe ejecutarse
    
    # Timestamps
    alert_minute = Column(String(16), nullable=False)    # "2025-01-28 14:35"
    received_at = Column(DateTime, nullable=False, default=func.now())
    opened_at = Column(DateTime, nullable=True)          # Cuándo se abrió la operación
    fecha_cierre = Column(DateTime, nullable=True)       # Cuándo se cerró
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'action': self.action.value if self.action else None,
            'price': self.price,
            'volume': self.volume,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'estatus': self.estatus.value if self.estatus else None,
            'beneficio': self.beneficio,
            'ratio_beneficio': self.ratio_beneficio,
            'ticket_mt5': self.ticket_mt5,
            'magic_number': self.magic_number,
            'processed': self.processed,
            'scheduled_execution': self.scheduled_execution.isoformat() if self.scheduled_execution else None,
            'alert_minute': self.alert_minute,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'fecha_cierre': self.fecha_cierre.isoformat() if self.fecha_cierre else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }