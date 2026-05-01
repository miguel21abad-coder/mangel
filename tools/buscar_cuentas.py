#!/usr/bin/env python3
"""
Busca cuentas de Instagram por nicho y devuelve métricas de engagement y alcance.
Uso: python buscar_cuentas.py --nicho "culturismo" --pais "España" --cantidad 10
     python buscar_cuentas.py --nicho "culturismo" --pais "España" --modo viral
"""

import argparse
import sys
import time
import re
from dataclasses import dataclass, field

try:
    from ddgs import DDGS
except ImportError:
    print("Instalando ddgs...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ddgs", "-q"])
    from ddgs import DDGS

try:
    import instaloader
except ImportError:
    print("Instalando instaloader...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "instaloader", "-q"])
    import instaloader


@dataclass
class CuentaInstagram:
    username: str
    seguidores: int
    siguiendo: int
    publicaciones: int
    engagement: float
    media_views: float        # media de visualizaciones por reel
    ratio_views: float        # media_views / seguidores (>1 = viral)
    reels_analizados: int
    verificada: bool
    bio: str


def buscar_usernames(nicho: str, pais: str, cantidad: int) -> list[str]:
    """Encuentra usernames de Instagram buscando en la web."""
    print(f"\n🔍 Buscando cuentas de '{nicho}' en {pais}...")

    queries = [
        f'site:instagram.com "{nicho}" {pais}',
        f'site:instagram.com "{nicho}" influencer {pais}',
        f'instagram "{nicho}" {pais} cuenta "@"',
        f'instagram "{nicho}" viral reels {pais}',
    ]

    usernames = set()
    with DDGS() as ddgs:
        for query in queries:
            if len(usernames) >= cantidad * 4:
                break
            try:
                results = ddgs.text(query, max_results=15)
                for r in results:
                    urls = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', r.get('href', '') + r.get('body', ''))
                    for u in urls:
                        if u not in ('p', 'reel', 'reels', 'stories', 'explore', 'accounts', 'tv', 'direct', 'share'):
                            usernames.add(u.lower())
                time.sleep(1)
            except Exception:
                continue

    return list(usernames)[:cantidad * 4]


def obtener_metricas(username: str, loader: instaloader.Instaloader) -> CuentaInstagram | None:
    """Obtiene métricas de un perfil público de Instagram."""
    try:
        profile = instaloader.Profile.from_username(loader.context, username)

        total_interacciones = 0
        total_views = 0
        num_posts = 0
        num_reels = 0

        for post in profile.get_posts():
            if num_posts >= 15:
                break

            total_interacciones += post.likes + post.comments

            # Reels y vídeos tienen view count
            if post.is_video and post.video_view_count:
                total_views += post.video_view_count
                num_reels += 1

            num_posts += 1
            time.sleep(0.4)

        followers = profile.followers
        if followers == 0:
            return None

        engagement = round((total_interacciones / num_posts) / followers * 100, 2) if num_posts > 0 else 0.0
        media_views = round(total_views / num_reels, 0) if num_reels > 0 else 0.0
        ratio_views = round(media_views / followers, 2) if followers > 0 and media_views > 0 else 0.0

        return CuentaInstagram(
            username=profile.username,
            seguidores=followers,
            siguiendo=profile.followees,
            publicaciones=profile.mediacount,
            engagement=engagement,
            media_views=media_views,
            ratio_views=ratio_views,
            reels_analizados=num_reels,
            verificada=profile.is_verified,
            bio=profile.biography[:80] + "..." if len(profile.biography) > 80 else profile.biography,
        )

    except Exception as e:
        print(f"  ⚠️  No se pudo obtener @{username}: {e}")
        return None


def fmt(n: float) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(int(n))


def clasificar_ratio(ratio: float) -> str:
    if ratio >= 3:
        return "🚀 Viral"
    if ratio >= 1:
        return "🔥 Despuntando"
    if ratio >= 0.5:
        return "✅ Bueno"
    if ratio >= 0.1:
        return "⚠️  Normal"
    return "—"


def main():
    parser = argparse.ArgumentParser(description="Busca cuentas de Instagram por nicho con métricas de alcance y engagement")
    parser.add_argument("--nicho", required=True, help="Nicho a buscar (ej: culturismo, fitness, yoga)")
    parser.add_argument("--pais", default="España", help="País de búsqueda (default: España)")
    parser.add_argument("--cantidad", type=int, default=10, help="Número de cuentas a analizar (default: 10)")
    parser.add_argument("--modo", default="engagement", choices=["engagement", "viral"],
                        help="Ordenar por engagement o por ratio views/seguidores (default: engagement)")
    parser.add_argument("--usuario", default="", help="Tu usuario de Instagram (recomendado para evitar bloqueos)")
    parser.add_argument("--password", default="", help="Tu contraseña de Instagram")
    args = parser.parse_args()

    loader = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_comments=False,
        save_metadata=False,
    )

    if args.usuario and args.password:
        print(f"🔑 Iniciando sesión como @{args.usuario}...")
        loader.login(args.usuario, args.password)

    usernames = buscar_usernames(args.nicho, args.pais, args.cantidad)

    if not usernames:
        print("❌ No se encontraron cuentas. Intenta con otro nicho o país.")
        sys.exit(1)

    print(f"\n📊 Analizando {min(len(usernames), args.cantidad)} cuentas...\n")

    cuentas = []
    analizadas = 0

    for username in usernames:
        if analizadas >= args.cantidad:
            break
        cuenta = obtener_metricas(username, loader)
        if cuenta and cuenta.seguidores >= 100_000:
            cuentas.append(cuenta)
            analizadas += 1
            viral = f" | ratio views: {cuenta.ratio_views}x" if cuenta.reels_analizados > 0 else ""
            print(f"  ✓ @{cuenta.username} — {fmt(cuenta.seguidores)} seguidores — {cuenta.engagement}% eng{viral}")
        time.sleep(2)

    if not cuentas:
        print("❌ No se pudieron analizar cuentas. Prueba añadiendo --usuario y --password.")
        sys.exit(1)

    # Ordenar según modo
    if args.modo == "viral":
        cuentas.sort(key=lambda c: c.ratio_views, reverse=True)
        criterio = "ratio views/seguidores (cuentas que despuntan)"
    else:
        cuentas.sort(key=lambda c: c.engagement, reverse=True)
        criterio = "engagement"

    print(f"\n{'='*90}")
    print(f"  RESULTADOS: '{args.nicho}' en {args.pais} — ordenado por {criterio}")
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

    print(f"\n  Ratio >1x = los reels llegan a más personas que sus seguidores → cuenta despuntando")
    print(f"  Engagement promedio Instagram 2026: ~0.45%")
    print(f"{'='*90}\n")


if __name__ == "__main__":
    main()
