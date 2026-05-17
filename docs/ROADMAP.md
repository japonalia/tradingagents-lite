# ROADMAP

1. ✅ **MVP creado**: TradingAgents Lite base para generar informe técnico/fundamental en Markdown.
2. ✅ **Prueba offline creada**: flujo local con `data/sample/NVDA_sample_daily.csv` y `tools/generate_sample_report.py`.
3. ✅ **Capa de proveedores activa**: abstracción de fuentes con implementación productiva en `yfinance`.
4. 🚧 **TVRemix MCP (integración inicial)**: cliente defensivo agregado, pendiente de validación completa del schema MCP (`tools/list` y `tools/call`) para mapear datos normalizados.
5. 🔜 Siguiente paso inmediato: volver a ejecutar `python tools/diagnose_tvremix.py` para mapear el `tools/list` real y luego conectar (`tools/list` / `tools/call`) a datos normalizados.
6. 🔜 Próximos pasos posteriores: scanner Nasdaq 100 y mejoras incrementales del pipeline.
