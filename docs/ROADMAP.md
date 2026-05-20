# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Fuerza relativa vs QQQ en scanner Nasdaq 100**: `RS vs QQQ = cambio de la acción - cambio de QQQ` con warning global si QQQ no está disponible.
7. ✅ **Paso actual**: infraestructura de catalizadores externos para Top final del scanner Nasdaq 100 (stub seguro, opcional, sin API real por defecto).
8. ✅ **Paso completado**: auditoría del universo Nasdaq 100 del scanner (inventario, chequeos de duplicados/formato y reporte en `reports/generated/nasdaq100_universe_audit.md`).
9. ✅ **Paso completado**: salida del scanner optimizada para GPT TradingAgents / Plantilla 7 (resumen ejecutivo, estado de candidata y limitaciones).
10. 🔜 **Próximo paso**: conectar un proveedor real de noticias/catalizadores sobre la infraestructura externa ya preparada.


## Estado intradía TVRemix (experimental)
- Paso actual: recalibración intradía del ranking para priorizar RVOL suficiente + fuerza real y penalizar movimientos sin volumen, extensiones sobre VWAP y perseguir precio sin confirmación.
- Mantener: fuerza relativa vs QQQ integrada al ranking y reporte, manteniendo `technical_intraday` cuando hay capa intradía.
- Paso en curso: consolidar catalizadores reales parseables sin ensuciar reporte ni disparar rate limits.
- Próximo paso: integración de catalizadores externos reales más confiables, manteniendo el modo estable del scanner.
