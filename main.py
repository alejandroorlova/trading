import uvicorn
from config import settings

def main():
    """Función principal simplificada"""
    
    print("=" * 50)
    print("🤖 BOT TRADING SIMPLIFICADO v1.0")
    print("=" * 50)
    print(f"🌐 URL: http://{settings.HOST}:{settings.PORT}")
    print(f"📡 Webhook: http://{settings.HOST}:{settings.PORT}/webhook/tradingview")
    print(f"📊 Alertas: http://{settings.HOST}:{settings.PORT}/alerts")
    print(f"📈 Stats: http://{settings.HOST}:{settings.PORT}/stats")
    print(f"💓 Health: http://{settings.HOST}:{settings.PORT}/health")
    print("=" * 50)
    print("✨ Características:")
    print("   • Recibe webhooks de TradingView")
    print("   • Guarda alertas en base de datos")
    print("   • Ignora duplicados en el mismo minuto")
    print("   • API REST para consultar datos")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "app:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()