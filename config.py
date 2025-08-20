import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Servidor
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5001"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # Base de datos
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///simple_trading.db")
    
    # MetaTrader 5
    MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "")
    MT5_PATH = os.getenv("MT5_PATH", "")  # Path opcional para MT5 portable
    
    # Trading Configuration
    POSITION_SIZE = float(os.getenv("POSITION_SIZE", "0.01"))
    MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "123456"))
    SLIPPAGE = int(os.getenv("SLIPPAGE", "10"))  # Slippage en puntos

     # Control por monto en vez de niveles fijos
    USE_SLTP = os.getenv("USE_SLTP", "True").lower() == "true"  # Usar niveles de SL/TP calculados
    TP_AMOUNT = float(os.getenv("TP_AMOUNT", os.getenv("TAKE_PROFIT_AMOUNT", "0")))  # Ganancia por monto
    SL_AMOUNT = float(os.getenv("SL_AMOUNT", os.getenv("STOP_LOSS_AMOUNT", "0")))    # Pérdida por monto
    
    # Stop Loss Configuration MEJORADA
    SL_MARGIN_TICKS = int(os.getenv("SL_MARGIN_TICKS", "5"))  # Ticks de margen para SL desde vela
    MIN_SL_DISTANCE = int(os.getenv("MIN_SL_DISTANCE", "20"))  # Distancia mínima de SL en ticks
    
    # NUEVO: Buffer de protección contra spread
    SPREAD_BUFFER_TICKS = int(os.getenv("SPREAD_BUFFER_TICKS", "10"))  # Buffer adicional para spread
    MAX_SPREAD_ALLOWED = int(os.getenv("MAX_SPREAD_ALLOWED", "30"))  # Spread máximo permitido para operar
    
    # NUEVO: Protección de entrada
    ENTRY_BUFFER_TICKS = int(os.getenv("ENTRY_BUFFER_TICKS", "5"))  # Buffer desde el precio actual para entrar
    WAIT_FOR_BETTER_PRICE = os.getenv("WAIT_FOR_BETTER_PRICE", "False").lower() == "true"
    
    # Ratios de beneficio
    REWARD_RATIOS = os.getenv("REWARD_RATIOS", "2,3,4,5,6,7,8,9")
    
    # Timing Configuration
    EXECUTION_MODE = os.getenv("EXECUTION_MODE", "NEXT_MINUTE")  # NEXT_MINUTE o DELAY
    EXECUTION_DELAY_SECONDS = int(os.getenv("EXECUTION_DELAY_SECONDS", "60"))
    PRICE_CHECK_INTERVAL = int(os.getenv("PRICE_CHECK_INTERVAL", "1"))
    
    # Trading Hours (opcional)
    TRADING_START_HOUR = int(os.getenv("TRADING_START_HOUR", "0"))
    TRADING_END_HOUR = int(os.getenv("TRADING_END_HOUR", "24"))
    
    # NUEVO: Control de riesgo mejorado
    MIN_RISK_REWARD_RATIO = float(os.getenv("MIN_RISK_REWARD_RATIO", "1.5"))  # Ratio mínimo para entrar
    SKIP_HIGH_SPREAD = os.getenv("SKIP_HIGH_SPREAD", "True").lower() == "true"

    TP_MODE = os.getenv("TP_MODE", "USD").upper()   # "USD" o "RATIO" (precio)
    RISK_MONEY_PER_TRADE = float(os.getenv("RISK_MONEY_PER_TRADE", "1.0"))
    TARGET_MONEY_PER_TRADE = float(os.getenv("TARGET_MONEY_PER_TRADE", "10.0"))
    
    @property
    def get_reward_ratios(self):
        """Convierte el string de ratios en una lista de enteros"""
        try:
            return [int(r.strip()) for r in self.REWARD_RATIOS.split(',')]
        except:
            return [2, 3, 4, 5, 6, 7, 8, 9]

settings = Settings()