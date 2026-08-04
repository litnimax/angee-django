"""Brand extraction from a public website, for the appearance wizard.

Given a URL this fetches the page and its stylesheets and reports the colour,
type and logo facts a theme can be built from. It lives in ``integrate`` because
this addon owns outbound HTTP: every fetch goes through the SSRF-pinned client,
which resolves once and dials the validated address, so a DNS rebind between the
check and the connect cannot redirect it at an internal host.

The analysis is deterministic on purpose — frequency and saturation over the
site's own declarations. That is auditable and testable, and it leaves a clean
seam for a model to *refine* the result (naming, pairing, dark-scheme taste)
rather than being the only thing standing between a URL and a theme.
"""

from __future__ import annotations

import colorsys
import math
import re
from collections import Counter
from typing import Any
from urllib.parse import urljoin

from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods

from angee.integrate.http import HttpClient
from angee.integrate.net import validate_public_url

PAGE_CAP_BYTES = 768 * 1024
"""Largest HTML document read. Enough for any landing page; bounds a hostile one."""

SHEET_CAP_BYTES = 512 * 1024
"""Largest single stylesheet read."""

MAX_STYLESHEETS = 4
"""Stylesheets fetched per analysis. The brand palette is always in the first few."""

_GENERIC_FAMILIES = {
    "sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded", "inherit",
    "initial", "unset", "revert", "-apple-system", "blinkmacsystemfont",
}

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})")
_LINK_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_ATTR_RE = re.compile(r"""(\w[\w-]*)\s*=\s*["']([^"']*)["']""")
_FONT_RE = re.compile(r"font-family\s*:\s*([^;{}]+)", re.IGNORECASE)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)


def _attrs(tag: str) -> dict[str, str]:
    """Return a tag's attributes lowercased by name."""

    return {name.lower(): value for name, value in _ATTR_RE.findall(tag)}


def _expand_hex(value: str) -> str:
    """Return a `#rrggbb` string from a 3- or 6-digit hex body."""

    body = value if len(value) == 6 else "".join(c * 2 for c in value)
    return f"#{body.lower()}"


def _hls(hex_colour: str) -> tuple[float, float, float]:
    """Return (hue, lightness, saturation) in 0..1 for a `#rrggbb` string."""

    r = int(hex_colour[1:3], 16) / 255
    g = int(hex_colour[3:5], 16) / 255
    b = int(hex_colour[5:7], 16) / 255
    return colorsys.rgb_to_hls(r, g, b)


def _colours(text: str) -> Counter[str]:
    """Count every colour literal in a CSS/HTML blob, normalised to `#rrggbb`."""

    found: Counter[str] = Counter()
    for match in _HEX_RE.findall(text):
        found[_expand_hex(match)] += 1
    for r, g, b in _RGB_RE.findall(text):
        try:
            channels = [min(255, int(v)) for v in (r, g, b)]
        except ValueError:  # pragma: no cover - regex already constrains digits
            continue
        found["#%02x%02x%02x" % tuple(channels)] += 1
    return found


def _brand_candidates(counts: Counter[str], limit: int = 6) -> list[dict[str, Any]]:
    """Rank saturated, mid-lightness colours by how much the site actually uses them.

    Weighting by ``count * saturation`` is what separates a real brand colour from
    an accidental one: a site mentions its accent everywhere, and a decorative
    gradient stop appears once. Near-duplicate hues collapse so the wizard offers
    genuinely different choices rather than six shades of the same red.
    """

    scored: list[tuple[float, str, int, float, float]] = []
    for hex_colour, count in counts.items():
        hue, lightness, saturation = _hls(hex_colour)
        if saturation < 0.30 or not (0.15 <= lightness <= 0.78):
            continue
        scored.append((count * saturation, hex_colour, count, hue, lightness))
    scored.sort(reverse=True)

    picked: list[dict[str, Any]] = []
    for score, hex_colour, count, hue, lightness in scored:
        duplicate = any(
            min(abs(hue - other["hue"]), 1 - abs(hue - other["hue"])) < 0.04
            and abs(lightness - other["lightness"]) < 0.12
            for other in picked
        )
        if duplicate:
            continue
        picked.append(
            {
                "hex": hex_colour,
                "weight": count,
                "score": round(score, 2),
                "hue": round(hue, 4),
                "lightness": round(lightness, 4),
            }
        )
        if len(picked) >= limit:
            break
    return picked


def _neutral_tint(counts: Counter[str]) -> str | None:
    """Return the temperature the site's greys lean towards, as a `#rrggbb`.

    A brand world is warm or cool long before it is red or green: the near-greys
    carry that, and reproducing it is what stops a re-skin looking like a recolour.
    Genuinely neutral greys (saturation under 3%) carry no temperature and are
    skipped so they cannot wash the average out.
    """

    total = 0
    x = y = 0.0
    for hex_colour, count in counts.items():
        hue, lightness, saturation = _hls(hex_colour)
        if not (0.03 <= saturation < 0.30) or not (0.08 <= lightness <= 0.92):
            continue
        angle = hue * 2 * math.pi
        x += math.cos(angle) * count
        y += math.sin(angle) * count
        total += count
    if total == 0:
        return None

    mean_hue = (math.atan2(y, x) / (2 * math.pi)) % 1.0
    r, g, b = colorsys.hls_to_rgb(mean_hue, 0.42, 0.38)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _fonts(text: str, limit: int = 3) -> list[str]:
    """Return the site's own font families, most declared first."""

    counts: Counter[str] = Counter()
    for declaration in _FONT_RE.findall(text):
        for raw in declaration.split(","):
            family = raw.strip().strip("\"'")
            if not family or family.lower() in _GENERIC_FAMILIES or family.startswith("var("):
                continue
            counts[family] += 1
            break  # only the first (preferred) family in each stack
    return [family for family, _ in counts.most_common(limit)]


def _site_identity(html: str, base_url: str) -> dict[str, str | None]:
    """Return the site name and the best available logo URL."""

    name: str | None = None
    logo: str | None = None
    title = _TITLE_RE.search(html)
    if title:
        name = re.sub(r"\s+", " ", title.group(1)).strip()[:120] or None

    for tag in _META_RE.findall(html):
        attrs = _attrs(tag)
        key = attrs.get("property") or attrs.get("name") or ""
        if key.lower() == "og:site_name" and attrs.get("content"):
            name = attrs["content"].strip()[:120]
        if key.lower() == "og:image" and attrs.get("content") and not logo:
            logo = urljoin(base_url, attrs["content"].strip())

    if not logo:
        for tag in _LINK_RE.findall(html):
            attrs = _attrs(tag)
            rel = (attrs.get("rel") or "").lower()
            if "icon" in rel and attrs.get("href"):
                logo = urljoin(base_url, attrs["href"].strip())
                break

    return {"siteName": name, "logo": logo}


def _stylesheet_urls(html: str, base_url: str) -> list[str]:
    """Return absolute stylesheet URLs declared by the page, in document order."""

    urls: list[str] = []
    for tag in _LINK_RE.findall(html):
        attrs = _attrs(tag)
        rel = (attrs.get("rel") or "").lower()
        href = attrs.get("href")
        if "stylesheet" in rel and href:
            urls.append(urljoin(base_url, href.strip()))
        if len(urls) >= MAX_STYLESHEETS:
            break
    return urls


def analyse(url: str) -> dict[str, Any]:
    """Fetch ``url`` and return the brand facts a theme can be generated from."""

    validate_public_url(url)
    client = HttpClient()

    page = client.download_capped(url, cap=PAGE_CAP_BYTES, follow_redirects=True)
    if not page:
        raise ValidationError("The site returned no readable content.")
    html = page.decode("utf-8", errors="replace")

    corpus = html
    sampled = 0
    for sheet_url in _stylesheet_urls(html, url):
        try:
            body = client.download_capped(sheet_url, cap=SHEET_CAP_BYTES, follow_redirects=True)
        except (ValidationError, OSError):
            continue  # one unreachable stylesheet must not fail the analysis
        if body:
            corpus += "\n" + body.decode("utf-8", errors="replace")
            sampled += 1
    for block in _STYLE_RE.findall(html):
        corpus += "\n" + block

    counts = _colours(corpus)
    return {
        "url": url,
        **_site_identity(html, url),
        "brandCandidates": _brand_candidates(counts),
        "neutralTint": _neutral_tint(counts),
        "fonts": _fonts(corpus),
        "sampledStylesheets": sampled,
        "coloursSeen": len(counts),
    }


@require_http_methods(["GET"])
def extract(request: HttpRequest) -> JsonResponse:
    """Analyse the ``url`` query parameter and return the extracted brand facts.

    Read-only and authenticated: it performs a server-side fetch on the caller's
    behalf, which is exactly the capability that must not be open to anonymous
    callers even with the SSRF guard in place.
    """

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=403)

    url = (request.GET.get("url") or "").strip()
    if not url:
        return JsonResponse({"error": "Pass ?url=<site>."}, status=400)
    if "://" not in url:
        url = f"https://{url}"

    try:
        return JsonResponse(analyse(url))
    except ValidationError as error:
        return JsonResponse({"error": "; ".join(error.messages)}, status=400)
    except OSError as error:
        return JsonResponse({"error": f"Could not reach the site: {error}"}, status=502)
