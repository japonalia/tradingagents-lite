# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. ✅ **TVRemix schema diagnostic completado**: inventario local de tools disponible y persistido en reportes sanitizados.
5. ✅ **TVRemix ticker individual funcionando**: mapeo inicial de ticker TVRemix (`get_quote`, `get_technicals`, `get_financials`, `get_news`, `get_ohlcv`) con fallback a yfinance.
6. ✅ **Fuerza relativa vs QQQ en scanner Nasdaq 100**: `RS vs QQQ = cambio de la acción - cambio de QQQ` con warning global si QQQ no está disponible.
7. ✅ **PREMARKET_CATALYST_ENGINE**: score 0–100, validación autoritativa/corroborada, clasificación de eventos y cobertura configurable de todo el universo declarado.
8. ✅ **Paso completado**: auditoría del universo Nasdaq 100 del scanner (inventario, chequeos de duplicados/formato y reporte en `reports/generated/nasdaq100_universe_audit.md`).
9. ✅ **Paso completado**: salida del scanner optimizada para GPT TradingAgents / Plantilla 7 (resumen ejecutivo, estado de candidata y limitaciones).
10. ✅ **Procedencia y frescura**: contrato por campo, estados explícitos y auditoría JSON por corrida con hash del universo.
11. ✅ **Suite de aceptación**: mezcla temporal, missing data, límites de score, ranking determinista y bloqueo de crédito para catalizadores no validados.
12. 🔜 **Pendiente externo**: conectar un segundo proveedor real de noticias/catalizadores. La capa opcional `external_catalysts` continúa como stub seguro hasta configurar un proveedor y credenciales autorizadas.


## Estado intradía TVRemix (experimental)
- Paso actual: recalibración intradía del ranking para priorizar RVOL suficiente + fuerza real y penalizar movimientos sin volumen, extensiones sobre VWAP y perseguir precio sin confirmación.
- Mantener: fuerza relativa vs QQQ integrada al ranking y reporte, manteniendo `technical_intraday` cuando hay capa intradía.
- Completado: consolidación determinista de catalizadores parseables, validación de fuentes y auditoría de cobertura.
- Próximo paso: integración de un segundo proveedor externo real, manteniendo el modo estable del scanner.
