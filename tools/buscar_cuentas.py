#!/usr/bin/env python3
"""
Busca cuentas de Instagram por nicho con métricas de engagement y alcance de reels.
Usa Apify como infraestructura cloud para evitar bloqueos de Instagram.

Uso:
  python buscar_cuentas.py --nicho "bodybuilding" --pais en --cantidad 15 --modo viral --token APIFY_TOKEN
  python buscar_cuentas.py --nicho "culturismo" --pais España --cantidad 10 --token APIFY_TOKEN

Obtén tu token gratis (sin tarjeta) en: https://apify.com
"""

import argparse
import sys
import re
from dataclasses import dataclass

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests


APIFY_BASE = "https://api.apify.com/v2"

# Hashtags por nicho que atraen cuentas grandes
HASHTAGS_NICHO = {
    "bodybuilding": ["ifbbpro", "classicphysique", "bodybuildingmotivation", "naturalbodybuilding", "mensphysique"],
    "fitness": ["fitnessmotivation", "personaltrainer", "fitnesscoach", "workout", "gymlife"],
    "culturismo": ["culturismofemenino", "culturismonatural", "fitness", "gymmotivation", "musculacion"],
    "yoga": ["yogainstructor", "yogateacher", "yogaeveryday", "yogalife", "yogapractice"],
    "crossfit": ["crossfitathlete", "crossfitlife", "wod", "functionalfitness", "crossfitgames"],
}


@dataclass
class CuentaInstagram:
    username: str
    seguidores: int
    publicaciones: int
    engagement: float
    media_views: float
    ratio_views: float
    reels_analizados: int
    verificada: bool
    bio: str


def apify_run(actor: str, run_input: dict, token: str, timeout: int = 120) -> list:
    """Lanza un actor de Apify y devuelve los resultados del dataset."""
    url = f"{APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items"
    params = {"token": token, "timeout": timeout, "memory": 512}
    resp = requests.post(url, params=params, json=run_input, timeout=timeout + 30)
    resp.raise_for_status()
    return resp.json()


def buscar_usernames_apify(nicho: str, pais: str, cantidad: int, token: str) -> list[str]:
    """Busca usuarios por hashtags de nicho usando Apify Instagram Hashtag Scraper."""
    solo_ingles = pais.lower() in ("en", "english", "inglés", "ingles")
    print(f"\n🔍 Buscando cuentas de '{nicho}' {'en inglés (global)' if solo_ingles else 'en ' + pais}...")

    # Hashtags principales del nicho
    nicho_key = nicho.lower().replace(" ", "")
    hashtags = [nicho_key] + HASHTAGS_NICHO.get(nicho.lower(), [])
    if not HASHTAGS_NICHO.get(nicho.lower()):
        # Fallback genérico
        hashtags += [f"{nicho_key}motivation", f"{nicho_key}life", f"{nicho_key}coach"]

    print(f"  Hashtags: {', '.join(['#'+h for h in hashtags[:5]])}...")

    run_input = {
        "hashtags": hashtags,
        "resultsLimit": 500,  # Más posts = más cuentas grandes encontradas
        "scrapeType": "posts",
    }

    try:
        items = apify_run("apify~instagram-hashtag-scraper", run_input, token, timeout=300)
    except Exception as e:
        print(f"  ⚠️  Error buscando hashtags: {e}")
        return []

    # Contar menciones por usuario (los que aparecen más veces = más activos en el nicho)
    conteo: dict[str, int] = {}
    for item in items:
        u = item.get("ownerUsername") or item.get("username")
        if u:
            conteo[u] = conteo.get(u, 0) + 1

    # Ordenar por actividad en el nicho
    ordenados = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
    usernames = [u for u, _ in ordenados]

    print(f"  → {len(usernames)} usuarios únicos encontrados en {len(items)} posts")
    return usernames


def obtener_perfiles_apify(usernames: list[str], token: str) -> list[dict]:
    """Obtiene métricas detalladas de perfiles usando Apify Instagram Profile Scraper."""
    run_input = {
        "usernames": usernames,
        "resultsType": "posts",
        "resultsLimit": 15,
    }

    try:
        return apify_run("apify~instagram-profile-scraper", run_input, token, timeout=300)
    except Exception as e:
        print(f"  ⚠️  Error obteniendo perfiles: {e}")
        return []


def procesar_perfil(data: dict) -> CuentaInstagram | None:
    """Extrae métricas de un perfil devuelto por Apify."""
    username = data.get("username") or data.get("inputUrl", "").split("/")[-1]
    seguidores = data.get("followersCount") or data.get("followers") or 0
    if not username or seguidores < 100_000:
        return None

    posts = data.get("latestPosts") or data.get("posts") or []
    total_interacciones = 0
    total_views = 0
    num_posts = len(posts)
    num_reels = 0

    for post in posts:
        total_interacciones += (post.get("likesCount") or 0) + (post.get("commentsCount") or 0)
        views = post.get("videoViewCount") or post.get("videoPlayCount") or 0
        if views:
            total_views += views
            num_reels += 1

    engagement = round((total_interacciones / num_posts) / seguidores * 100, 2) if num_posts > 0 and seguidores > 0 else 0.0
    media_views = round(total_views / num_reels, 0) if num_reels > 0 else 0.0
    ratio_views = round(media_views / seguidores, 2) if seguidores > 0 and media_views > 0 else 0.0

    bio = data.get("biography") or data.get("bio") or ""

    return CuentaInstagram(
        username=username,
        seguidores=seguidores,
        publicaciones=data.get("postsCount") or data.get("mediaCount") or 0,
        engagement=engagement,
        media_views=media_views,
        ratio_views=ratio_views,
        reels_analizados=num_reels,
        verificada=data.get("verified") or data.get("isVerified") or False,
        bio=bio[:80] + "..." if len(bio) > 80 else bio,
    )


PALABRAS_EN = {
    "the","and","for","with","your","you","this","that","from","are","was",
    "have","has","been","will","not","but","they","his","her","our","more",
    "all","about","just","can","get","my","me","we","at","be","to","of",
    "in","is","it","on","workout","training","gains","gym","fitness","coach",
    "follow","link","bio","shop","online","weight","muscle","diet","athlete",
}
PALABRAS_ES = {
    "de","la","el","en","que","los","las","con","por","para","del","una",
    "uno","es","se","mi","tu","su","no","si","entreno","entrenamiento",
    "fuerza","culturismo","dieta","nutrición",
}


def es_ingles(texto: str) -> bool:
    palabras = re.findall(r"[a-záéíóúüñ]+", texto.lower())
    if not palabras:
        return True  # Sin texto = no descartamos
    hits_en = sum(1 for p in palabras if p in PALABRAS_EN)
    hits_es = sum(1 for p in palabras if p in PALABRAS_ES)
    return hits_en >= hits_es  # En caso de empate, consideramos inglés


def fmt(n: float) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(int(n))


def clasificar_ratio(ratio: float) -> str:
    if ratio >= 3:   return "🚀 Viral"
    if ratio >= 1:   return "🔥 Despuntando"
    if ratio >= 0.5: return "✅ Bueno"
    if ratio >= 0.1: return "⚠️  Normal"
    return "—"


def main():
    parser = argparse.ArgumentParser(description="Busca cuentas de Instagram por nicho vía Apify")
    parser.add_argument("--nicho",    required=True,  help="Nicho a buscar (ej: bodybuilding, fitness, yoga)")
    parser.add_argument("--pais",     default="España", help="País o 'en' para inglés global")
    parser.add_argument("--cantidad", type=int, default=10, help="Cuentas a analizar (default: 10)")
    parser.add_argument("--modo",     default="viral", choices=["engagement", "viral"],
                        help="Ordenar por engagement o ratio views/seguidores (default: viral)")
    parser.add_argument("--token",    required=True,  help="Token de API de Apify (gratis en apify.com)")
    args = parser.parse_args()

    solo_ingles = args.pais.lower() in ("en", "english", "inglés", "ingles")

    usernames = buscar_usernames_apify(args.nicho, args.pais, args.cantidad, args.token)
    if not usernames:
        print("❌ No se encontraron cuentas para ese nicho.")
        sys.exit(1)

    print(f"\n📊 Obteniendo métricas de perfiles...")
    cuentas = []
    batch_size = 20

    for i in range(0, len(usernames), batch_size):
        if len(cuentas) >= args.cantidad:
            break
        batch = usernames[i:i + batch_size]
        perfiles = obtener_perfiles_apify(batch, args.token)

        for data in perfiles:
            if len(cuentas) >= args.cantidad:
                break
            cuenta = procesar_perfil(data)
            if not cuenta:
                continue
            if solo_ingles and not es_ingles(cuenta.bio):
                print(f"  ⏭  @{cuenta.username} descartada (no en inglés)")
                continue
            cuentas.append(cuenta)
            views_str = f" | views avg: {fmt(cuenta.media_views)} (ratio {cuenta.ratio_views}x)" if cuenta.reels_analizados > 0 else ""
            print(f"  ✓ @{cuenta.username} — {fmt(cuenta.seguidores)} seguidores — {cuenta.engagement}% eng{views_str}")

    if not cuentas:
        print("❌ Ninguna cuenta superó los 100K seguidores con los filtros aplicados.")
        sys.exit(1)

    if args.modo == "viral":
        cuentas.sort(key=lambda c: c.ratio_views, reverse=True)
        criterio = "ratio views/seguidores"
    else:
        cuentas.sort(key=lambda c: c.engagement, reverse=True)
        criterio = "engagement"

    print(f"\n{'='*90}")
    print(f"  RESULTADOS: '{args.nicho}' {'(inglés, global)' if solo_ingles else args.pais} — ordenado por {criterio}")
    print(f"{'='*90}\n")
    print(f"{'#':<3} {'Usuario':<22} {'Seguidores':<11} {'Avg Views':<11} {'Ratio':<8} {'Eng%':<8} {'Alcance'}")
    print("-" * 90)

    for i, c in enumerate(cuentas, 1):
        v = "✓" if c.verificada else " "
        views_str = fmt(c.media_views) if c.reels_analizados > 0 else "—"
        ratio_str = f"{c.ratio_views}x" if c.reels_analizados > 0 else "—"
        print(f"{i:<3} @{c.username+v:<21} {fmt(c.seguidores):<11} {views_str:<11} {ratio_str:<8} {c.engagement}%{'':4} {clasificar_ratio(c.ratio_views)}")
        if c.bio:
            print(f"    └─ {c.bio}")

    print(f"\n  Ratio >1x = reels llegan a más personas que sus seguidores → cuenta despuntando")
    print(f"  Engagement promedio Instagram 2026: ~0.45%")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
