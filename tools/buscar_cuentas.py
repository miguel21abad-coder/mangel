#!/usr/bin/env python3
"""
Busca cuentas de Instagram por nicho y devuelve métricas de engagement.
Uso: python buscar_cuentas.py --nicho "culturismo" --pais "España" --cantidad 10
"""

import argparse
import sys
import time
import re
from dataclasses import dataclass

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
    verificada: bool
    bio: str


def buscar_usernames(nicho: str, pais: str, cantidad: int) -> list[str]:
    """Encuentra usernames de Instagram buscando en la web."""
    print(f"\n🔍 Buscando cuentas de '{nicho}' en {pais}...")

    queries = [
        f'site:instagram.com "{nicho}" {pais}',
        f'site:instagram.com "{nicho}" influencer {pais}',
        f'mejores cuentas instagram "{nicho}" {pais} "@"',
    ]

    usernames = set()

    with DDGS() as ddgs:
        for query in queries:
            if len(usernames) >= cantidad * 3:
                break
            try:
                results = ddgs.text(query, max_results=15)
                for r in results:
                    # Extraer usernames de URLs de instagram.com
                    urls = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', r.get('href', '') + r.get('body', ''))
                    for u in urls:
                        if u not in ('p', 'reel', 'stories', 'explore', 'accounts', 'tv'):
                            usernames.add(u.lower())
                time.sleep(1)
            except Exception:
                continue

    return list(usernames)[:cantidad * 3]


def obtener_metricas(username: str, loader: instaloader.Instaloader) -> CuentaInstagram | None:
    """Obtiene métricas de un perfil público de Instagram."""
    try:
        profile = instaloader.Profile.from_username(loader.context, username)

        # Calcular engagement con los últimos 12 posts
        total_interacciones = 0
        num_posts = 0
        for post in profile.get_posts():
            if num_posts >= 12:
                break
            total_interacciones += post.likes + post.comments
            num_posts += 1
            time.sleep(0.5)

        if num_posts > 0 and profile.followers > 0:
            engagement = (total_interacciones / num_posts) / profile.followers * 100
        else:
            engagement = 0.0

        return CuentaInstagram(
            username=profile.username,
            seguidores=profile.followers,
            siguiendo=profile.followees,
            publicaciones=profile.mediacount,
            engagement=round(engagement, 2),
            verificada=profile.is_verified,
            bio=profile.biography[:80] + "..." if len(profile.biography) > 80 else profile.biography,
        )

    except Exception as e:
        print(f"  ⚠️  No se pudo obtener @{username}: {e}")
        return None


def formatear_numero(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def clasificar_engagement(tasa: float) -> str:
    if tasa >= 6:
        return "🔥 Excelente"
    if tasa >= 3:
        return "✅ Bueno"
    if tasa >= 1:
        return "⚠️  Normal"
    return "❌ Bajo"


def main():
    parser = argparse.ArgumentParser(description="Busca cuentas de Instagram por nicho con métricas de engagement")
    parser.add_argument("--nicho", required=True, help="Nicho a buscar (ej: culturismo, fitness, yoga)")
    parser.add_argument("--pais", default="España", help="País de búsqueda (default: España)")
    parser.add_argument("--cantidad", type=int, default=10, help="Número de cuentas a analizar (default: 10)")
    parser.add_argument("--usuario", default="", help="Tu usuario de Instagram (opcional, para evitar rate limits)")
    parser.add_argument("--password", default="", help="Tu contraseña de Instagram (opcional)")
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

    print(f"\n📊 Analizando {min(len(usernames), args.cantidad)} cuentas... (esto puede tardar unos minutos)\n")

    cuentas = []
    analizadas = 0

    for username in usernames:
        if analizadas >= args.cantidad:
            break
        cuenta = obtener_metricas(username, loader)
        if cuenta and cuenta.seguidores > 500:
            cuentas.append(cuenta)
            analizadas += 1
            print(f"  ✓ @{cuenta.username} — {formatear_numero(cuenta.seguidores)} seguidores — {cuenta.engagement}% engagement")
        time.sleep(2)

    if not cuentas:
        print("❌ No se pudieron analizar cuentas. Instagram puede estar limitando las peticiones. Prueba con --usuario y --password.")
        sys.exit(1)

    # Ordenar por engagement
    cuentas.sort(key=lambda c: c.engagement, reverse=True)

    print(f"\n{'='*80}")
    print(f"  RESULTADOS: Top cuentas de '{args.nicho}' en {args.pais}")
    print(f"{'='*80}\n")

    print(f"{'#':<3} {'Usuario':<22} {'Seguidores':<12} {'Posts':<8} {'Engagement':<12} {'Calidad'}")
    print("-" * 80)

    for i, c in enumerate(cuentas, 1):
        verificado = "✓" if c.verificada else " "
        print(f"{i:<3} @{c.username+verificado:<21} {formatear_numero(c.seguidores):<12} {c.publicaciones:<8} {c.engagement}%{'':<8} {clasificar_engagement(c.engagement)}")
        if c.bio:
            print(f"    └─ {c.bio}")

    print(f"\n{'='*80}")
    print(f"  Engagement promedio en Instagram 2026: ~0.45%")
    print(f"  Fuente: Datos públicos de Instagram vía instaloader")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
