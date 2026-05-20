# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Fuerza relativa vs QQQ en scanner Nasdaq 100**: `RS vs QQQ = cambio de la acción - cambio de QQQ` con warning global si QQQ no está disponible.
7. ✅ **Paso actual**: recalibración intradía del scoring Nasdaq 100 (penalización por RVOL bajo, extensión excesiva y cap de score sin catalizador confirmado).
8. 🚧 **Paso actual en curso**: capa de catalizadores reales parseables (diagnóstico `get_news`, consulta prudente solo en Top final, sin romper modo estable).
9. ✅ **Paso completado**: salida del scanner optimizada para GPT TradingAgents / Plantilla 7 (resumen ejecutivo, estado de candidata y limitaciones).
10. 🔜 **Próximo paso**: auditoría del universo Nasdaq 100 y refuerzo de catalizadores externos.


## Estado intradía TVRemix (experimental)
- Paso actual: recalibración intradía del ranking para priorizar RVOL suficiente + fuerza real y penalizar movimientos sin volumen, extensiones sobre VWAP y perseguir precio sin confirmación.
- Mantener: fuerza relativa vs QQQ integrada al ranking y reporte, manteniendo `technical_intraday` cuando hay capa intradía.
- Paso en curso: consolidar catalizadores reales parseables sin ensuciar reporte ni disparar rate limits.
- Próximo paso: auditoría del universo Nasdaq 100 (símbolos/cobertura real) y/o integración de catalizadores externos más confiables.
