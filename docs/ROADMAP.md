# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Paso actual**: batching real en scanner Nasdaq 100 (`get_quotes_batch` en chunks <= 50), técnicos por fases (`--technical-top-n` con `analyze_multi_timeframe_batch` y fallback acotado), y warnings globales anti-ruido para rate limits 429.
7. 🔜 **Próximos pasos**: RVOL, VWAP, premarket high/low y fuerza relativa vs QQQ.
