from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from webhook_service import webhook_service
from database import create_tables
from config import settings
from trading_executor import trading_executor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bot Trading Automatizado MT5",
    description="Sistema completo de trading con MT5, gestión de SL/TP y múltiples ratios",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    logger.info("🚀 Iniciando Bot Trading Automatizado MT5...")
    logger.info(f"📊 Ratios configurados: {settings.get_reward_ratios}")
    logger.info(f"⏱️ Delay de ejecución: {settings.EXECUTION_DELAY_SECONDS} segundos")
    logger.info(f"📏 Margen SL: {settings.SL_MARGIN_TICKS} ticks")
    
    # Crear tablas si no existen
    create_tables()
    
    # Iniciar el ejecutor de trading
    trading_executor.start()
    
    logger.info("✅ Bot listo para recibir alertas y ejecutar operaciones")

@app.on_event("shutdown")
async def shutdown():
    logger.info("🛑 Deteniendo Bot Trading...")
    trading_executor.stop()
    logger.info("👋 Bot detenido correctamente")

@app.get("/")
async def root():
    return {
        "service": "Bot Trading Automatizado MT5",
        "version": "3.0.0",
        "status": "running",
        "features": [
            "Recepción de webhooks de TradingView",
            "Ejecución automática en MT5",
            "Gestión de múltiples ratios de beneficio",
            "Monitoreo automático de SL/TP",
            "Cálculo de SL basado en vela anterior",
            "Control de duplicados por minuto"
        ],
        "endpoints": {
            "webhook": "/webhook/tradingview",
            "alerts": "/alerts",
            "stats": "/stats",
            "config": "/config",
            "health": "/health"
        },
        "mt5_config": {
            "login": settings.MT5_LOGIN,
            "server": settings.MT5_SERVER,
            "magic_number": settings.MAGIC_NUMBER,
            "execution_delay": f"{settings.EXECUTION_DELAY_SECONDS} segundos"
        },
        "trading_config": {
            "reward_ratios": settings.get_reward_ratios,
            "position_size": settings.POSITION_SIZE,
            "sl_margin_ticks": settings.SL_MARGIN_TICKS,
            "min_sl_distance": settings.MIN_SL_DISTANCE
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Verificar estado del sistema"""
    from mt5_service import mt5_service
    
    mt5_connected = mt5_service.initialized
    executor_running = trading_executor.running
    
    status = "healthy" if (mt5_connected and executor_running) else "degraded"
    
    return {
        "status": status,
        "components": {
            "api": "healthy",
            "mt5": "connected" if mt5_connected else "disconnected",
            "executor": "running" if executor_running else "stopped"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/tradingview")
async def webhook_tradingview(request: Request):
    """
    🎯 Endpoint para alertas de TradingView
    
    Formato JSON esperado:
    {
        "symbol": "XAUUSD",
        "action": "BUY"
    }
    
    Este endpoint:
    1. Crea múltiples alertas según los ratios configurados
    2. Programa la ejecución para el minuto siguiente
    3. El ejecutor abrirá las operaciones automáticamente
    """
    try:
        # Obtener datos JSON
        data = await request.json()
        
        if not data:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Payload JSON vacío",
                    "expected_format": {"symbol": "XAUUSD", "action": "BUY"}
                }
            )
        
        logger.info(f"📨 Webhook TradingView recibido: {data}")
        
        # Procesar alerta
        result = webhook_service.process_tradingview_alert(data)
        
        # Respuesta según resultado
        if result["success"]:
            logger.info(f"✅ {result.get('alerts_created')} alertas creadas y programadas")
            return {
                "status": "received",
                "message": result.get("message"),
                "execution_info": f"Las operaciones se ejecutarán a las {result.get('execution_time')}",
                "result": result
            }
        else:
            # Determinar código de respuesta
            if result.get("ignored"):
                logger.warning(f"🚫 Alerta duplicada ignorada")
                status_code = 409  # Conflict
            else:
                logger.error(f"❌ Error de validación: {result.get('error')}")
                status_code = 400  # Bad Request
                
            raise HTTPException(status_code=status_code, detail=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error interno webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno del servidor", 
                "details": str(e),
                "expected_format": {"symbol": "XAUUSD", "action": "BUY"}
            }
        )

@app.get("/alerts")
async def get_alerts(limit: int = 50):
    """Obtener alertas recientes con todos sus detalles"""
    result = webhook_service.get_recent_alerts(limit)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result)

@app.get("/alerts/status/{status}")
async def get_alerts_by_status(status: str):
    """
    Obtener alertas por estado
    Estados válidos: PENDIENTE, ABIERTA, SL, TP, CANCELADA
    """
    result = webhook_service.get_alerts_by_status(status)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400 if "error" in result else 500, detail=result)

@app.get("/stats")
async def get_stats():
    """Obtener estadísticas completas del sistema"""
    result = webhook_service.get_stats()
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result)

@app.get("/config")
async def get_config():
    """Obtener configuración actual del sistema"""
    return {
        "server": {
            "host": settings.HOST,
            "port": settings.PORT,
            "debug": settings.DEBUG
        },
        "mt5": {
            "login": settings.MT5_LOGIN,
            "server": settings.MT5_SERVER,
            "connected": trading_executor.running
        },
        "trading": {
            "position_size": settings.POSITION_SIZE,
            "reward_ratios": settings.get_reward_ratios,
            "alerts_per_signal": len(settings.get_reward_ratios),
            "magic_number": settings.MAGIC_NUMBER,
            "slippage": settings.SLIPPAGE
        },
        "risk_management": {
            "sl_margin_ticks": settings.SL_MARGIN_TICKS,
            "min_sl_distance": settings.MIN_SL_DISTANCE
        },
        "timing": {
            "execution_delay_seconds": settings.EXECUTION_DELAY_SECONDS,
            "price_check_interval": settings.PRICE_CHECK_INTERVAL,
            "trading_hours": {
                "start": settings.TRADING_START_HOUR,
                "end": settings.TRADING_END_HOUR
            }
        },
        "database": {
            "url": settings.DATABASE_URL.split("///")[-1] if "///" in settings.DATABASE_URL else settings.DATABASE_URL
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/executor/status")
async def executor_status():
    """Obtener estado detallado del ejecutor"""
    try:
        status = trading_executor.get_status_summary()
        
        return {
            "status": "success",
            "executor": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})