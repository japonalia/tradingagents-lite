# Scanner Nasdaq 100

- Fecha/hora generación (local): **2026-05-19T18:52:57+00:00**
- Fuente primaria: **tvremix**

## Modo del scanner
- degraded: Scanner degradado por fallos de datos.

## Calidad de datos
- Símbolos en universo: **98**
- Candidatas evaluadas: **98**
- Candidatas mostradas: **10**
- Quotes disponibles: **0**
- Intradía disponibles: **0**
- RVOL disponibles: **0**
- VWAP disponibles: **0**
- Premarket disponibles: **0**
- Intradía vía run_screener: **0**
- Intradía vía get_symbol_data: **0**
- Técnicos disponibles: **0**
- Técnicos batch disponibles: **0**
- Técnicos fallback individuales: **0**
- Técnicos no disponibles: **10**
- Catalizadores consultados: **5**
- QQQ referencia: **N/A**
- Fuerza relativa disponible: **0/98**
- OHLCV intradía consultados: **5**
- OHLCV intradía disponibles: **0**
- OHLCV visibles en Top mostrado: **0**
- VWAP calculado desde barras disponible: **0**
- Completas: **0**
- Con datos faltantes: **98** (incluye símbolos fuera del subconjunto técnico consultado)
- Datos no disponibles detectados: **change_percent, price, rsi, technical_rating, volume**

## Top candidatas

| Ranking | Ticker | Precio | Variación % | RS vs QQQ | Volumen | RVOL | VWAP | Gap/PM | Rating técnico | RSI | Catalizador | Score | Riesgo / warnings |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|---|---:|---|
| 1 | NASDAQ:ADBE | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; niveles intradía OHLCV no disponibles |
| 2 | NASDAQ:ADI | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; niveles intradía OHLCV no disponibles |
| 3 | NASDAQ:ADP | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; niveles intradía OHLCV no disponibles |
| 4 | NASDAQ:ADSK | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; niveles intradía OHLCV no disponibles |
| 5 | NASDAQ:AEP | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; niveles intradía OHLCV no disponibles |
| 6 | NASDAQ:AMAT | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; Sin change_percent. |
| 7 | NASDAQ:AMD | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; Sin change_percent. |
| 8 | NASDAQ:AMGN | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; Sin change_percent. |
| 9 | NASDAQ:AMZN | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; Sin change_percent. |
| 10 | NASDAQ:ANSS | N/A | N/A | N/A | N/A | N/A | N/A | g:N/A/pm:N/A | N/A | N/A | Sin catalizador confirmado | 10.0 | quote no disponible en get_quotes_batch; technicals no disponibles en analyze_multi_timeframe_batch/get_technicals; Sin change_percent. |

## Fuerza relativa vs QQQ

- Fuerza relativa no disponible en esta corrida.

## Catalizadores reales detectados

No se detectaron catalizadores reales parseables.

## Niveles intradía destacados

- Sin niveles intradía OHLCV disponibles en esta corrida.

## Warnings globales

- get_quotes_batch chunk 1 falló (size=50): TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_quotes_batch chunk 2 falló (size=48): TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_quotes_batch sin payload parseable en todos los chunks.
- get_quotes_batch chunk 1 falló (size=1): TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- QQQ no disponible; fuerza relativa no calculada
- run_screener falló: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- run_screener sin cobertura útil; usando get_symbol_data para Top 10
- get_symbol_data falló para NASDAQ:ADBE: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:ADI: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:ADP: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:ADSK: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:AEP: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:AMAT: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:AMD: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:AMGN: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:AMZN: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_symbol_data falló para NASDAQ:ANSS: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- analyze_multi_timeframe_batch falló globalmente: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- fallback técnicos individuales limitado a 5/10 símbolos para evitar rate limit
- get_technicals falló para NASDAQ:ADBE: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_technicals falló para NASDAQ:ADI: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_technicals falló para NASDAQ:ADP: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_technicals falló para NASDAQ:ADSK: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_technicals falló para NASDAQ:AEP: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_ohlcv intradía falló para NASDAQ:ADBE: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_ohlcv intradía falló para NASDAQ:ADI: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_ohlcv intradía falló para NASDAQ:ADP: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_ohlcv intradía falló para NASDAQ:ADSK: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_ohlcv intradía falló para NASDAQ:AEP: TVRemix MCP no está configurado. Define TVREMIX_MCP_URL y TVREMIX_API_KEY.
- get_news sin titulares parseables para 5 símbolos
- OHLCV calculado para 5 candidatos; 0 visible en Top mostrado tras reordenación.

## Datos intradía destacados

- Sin datos intradía destacados.

## No es señal ejecutable
Este reporte es informativo y no constituye una orden, recomendación ni señal ejecutable de trading.

No usar como señal ejecutable intradía.
