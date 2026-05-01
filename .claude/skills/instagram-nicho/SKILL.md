---
name: instagram-nicho
description: Busca y analiza cuentas de Instagram por nicho usando el script tools/buscar_cuentas.py. Usar cuando el usuario pida encontrar cuentas de Instagram en un nicho específico, ver métricas de engagement, o investigar competidores/referentes.
---

# Búsqueda de Cuentas de Instagram por Nicho

Herramienta propia que replica las funciones básicas de Heepsy de forma gratuita.

## Cómo funciona

El script `tools/buscar_cuentas.py`:
1. Busca en DuckDuckGo cuentas de Instagram relacionadas con el nicho
2. Extrae usernames de URLs de instagram.com
3. Usa `instaloader` para obtener métricas públicas de cada perfil
4. Calcula el engagement con los últimos 12 posts
5. Devuelve una tabla ordenada por engagement

## Uso básico

```bash
python tools/buscar_cuentas.py --nicho "culturismo" --pais "España" --cantidad 10
```

## Parámetros

- `--nicho` (requerido): el nicho a buscar (ej: "culturismo", "yoga", "crossfit", "nutrición deportiva")
- `--pais` (default: España): país de búsqueda
- `--cantidad` (default: 10): cuántas cuentas analizar
- `--usuario` y `--password`: cuenta de Instagram propia (opcional, reduce rate limiting)

## Clasificación de engagement

- 🔥 Excelente: >6%
- ✅ Bueno: 3–6%
- ⚠️ Normal: 1–3%
- ❌ Bajo: <1%
- Referencia: el promedio de Instagram en 2026 es ~0.45%

## Cuándo recomendar usar credenciales

Si Instagram empieza a bloquear las peticiones (error 429 o similar), sugerir al usuario que añada `--usuario` y `--password` con una cuenta secundaria. Nunca pedirle la contraseña de su cuenta principal.

## Instalación de dependencias

El script las instala automáticamente. Si hay problemas:
```bash
pip install instaloader duckduckgo-search
```

## Limitaciones

- Instagram puede limitar peticiones sin login (rate limiting)
- Los resultados de búsqueda en DuckDuckGo no son exhaustivos — puede no encontrar todas las cuentas relevantes
- No muestra datos de audiencia (edad, país) — eso requiere herramientas de pago
