# Auditoría técnica de `TauricResearch/TradingAgents` (referencial, sin integración)

> Fecha de auditoría: 2026-05-17 (UTC)
> 
> Alcance: documentación y análisis conceptual del repositorio original, **sin copiar código** dentro de `src/`, **sin ejecutar** el proyecto original, y **sin configurar APIs**.

## 1) Estructura principal del repositorio original

A partir de la página pública del repositorio y documentación asociada, la estructura top-level observada es:

- `assets/`
- `cli/`
- `scripts/`
- `tests/`
- `tradingagents/` (núcleo del framework)
- archivos de configuración (`.env.example`, `.env.enterprise.example`, `pyproject/setup`, etc.)

En el núcleo `tradingagents/` aparecen (por referencias públicas) módulos típicos:

- `tradingagents/agents/` (analistas, researchers, trader, risk, managers)
- `tradingagents/graph/` (flujo secuencial y lógica de propagación)
- `tradingagents/dataflows/` (conectores a mercado/noticias/redes)
- `tradingagents/default_config.py`

## 2) Lista de agentes identificados

Con base en rutas públicas listadas en documentación/indexadores:

### Analistas
- `analysts/fundamentals_analyst.py`
- `analysts/market_analyst.py`
- `analysts/news_analyst.py`
- `analysts/social_media_analyst.py`

### Researchers (debate bull/bear)
- `researchers/bull_researcher.py`
- `researchers/bear_researcher.py`

### Gestión y decisión
- `managers/research_manager.py`
- `trader/trader.py`
- `managers/risk_manager.py`

### Risk debate
- `risk_mgmt/aggressive_debator.py` (aparece también con typo `aggresive` en algunas referencias)
- `risk_mgmt/neutral_debator.py`
- `risk_mgmt/conservative_debator.py`

### Utilidades de agente
- `agents/utils/agent_states.py`
- `agents/utils/agent_utils.py`
- `agents/utils/memory.py`

## 3) Flujo general de análisis (pipeline observado)

Patrón general descrito por el propio proyecto y documentación secundaria:

1. **Analyst Team**: compila señales (fundamental, técnico/mercado, noticias, social).
2. **Research Team**: confronta tesis alcista/bajista.
3. **Research Manager**: resume/normaliza hallazgos.
4. **Trader Agent**: convierte hallazgos en propuesta de acción.
5. **Risk Management Team**: debate perfil de riesgo (agresivo/neutral/conservador).
6. **Risk Manager / Portfolio Manager**: decisión final o señal procesada.

Arquitecturalmente se implementa como grafo/pipeline (LangGraph) con estado compartido y pasos secuenciales.

## 4) Archivos/carpetas donde están prompts y lógica de agentes

Ubicaciones candidatas en el repositorio original:

- `tradingagents/agents/**` → lógica por rol y prompts de cada agente.
- `tradingagents/graph/**` → orquestación y transiciones entre agentes.
- `cli/**` → entrada interactiva del usuario (selección ticker, fecha, provider, etc.).
- `tradingagents/default_config.py` → defaults de modelo/proveedor/parámetros.
- `scripts/**` → utilidades operativas (setup, ejecución auxiliar, etc.).

## 5) Puntos donde se llaman modelos LLM externos

Se observan múltiples indicios explícitos de integración multi-proveedor:

- Variables de entorno documentadas para:
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `XAI_API_KEY`
  - `DEEPSEEK_API_KEY`
  - `DASHSCOPE_API_KEY` (Qwen)
  - `ZHIPU_API_KEY` (GLM)
  - `OPENROUTER_API_KEY`
- Soporte mencionado para `ollama` en configuración.
- Changelog/release notes mencionan `OpenAI Responses API` y mejoras de structured output.

En términos de código, las llamadas suelen concentrarse en:

- constructores de agentes en `tradingagents/agents/**`,
- capa de configuración de modelos/proveedores,
- pipeline de ejecución que invoca cada rol del grafo.

## 6) Fuentes de datos usadas por el proyecto original

Por rutas públicas referenciadas:

- `dataflows/yfin_utils.py` → Yahoo Finance (precios/mercado)
- `dataflows/finnhub_utils.py` → Finnhub (mercado/noticias)
- `dataflows/googlenews_utils.py` → Google News
- `dataflows/reddit_utils.py` → Reddit/social
- `dataflows/stockstats_utils.py` → indicadores técnicos
- `ALPHA_VANTAGE_API_KEY` aparece en documentación de APIs requeridas

## 7) Partes útiles para inspirar TradingAgents Lite

1. **Descomposición por roles** (analistas + research + trader + risk) separando responsabilidades.
2. **Pipeline determinista por etapas** con estado explícito entre nodos.
3. **Interfaz CLI** para parametrizar ticker/fecha/profundidad.
4. **Capa dataflows desacoplada** del motor de decisión.
5. **Post-procesado de señal** (normalización y decisión final trazable).

## 8) Partes a excluir en TradingAgents Lite (sin LLM externos)

1. **Toda llamada a proveedores LLM externos** (OpenAI/Anthropic/Gemini/OpenRouter/DeepSeek/xAI/Qwen/GLM/Ollama).
2. **Dependencia de API keys de LLM** en runtime.
3. **Prompts complejos orientados a razonamiento de modelo remoto**.
4. **Variabilidad no determinista por temperatura/model sampling**.

## 9) Recomendación de adaptación Lite (siguiente paso)

Para TradingAgents Lite, mantener el mismo esqueleto lógico pero reemplazar nodos LLM por:

- reglas explícitas,
- scoring cuantitativo reproducible,
- plantillas de texto deterministas,
- agregación de señales con pesos configurables.

---

## Notas metodológicas y limitaciones

- **No se integró ni ejecutó** el repositorio original.
- La clonación directa vía `git clone` no estuvo disponible en este entorno (error de red `403`), por lo que la auditoría se realizó con inspección web de documentación pública, listados de archivos y descripciones del propio repositorio.
- Este documento está orientado a diseño y planificación; cuando haya conectividad de clonación, conviene validar cada ruta/archivo sobre el árbol real para cerrar posibles diferencias menores de nombres.
