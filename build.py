#!/usr/bin/env python3
"""
Tendering.me — statički generator.

    pip install markdown        # jednom
    python3 build.py            # prije svakog commita

Ulaz:   content/**/*.md   (front matter + Markdown)
        templates/page.html
        index.html        (ME početna — ručno održavana)
Izlaz:  <url>/index.html za svaku stranicu, en/index.html, sitemap.xml,
        praksa/index.html i praksa/tema/<slug>/index.html

Vercel ne pokreće ništa — generisani HTML se commituje.
"""
import json, re, html, datetime
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
SITE = "https://tendering.me"
CONTENT = ROOT / "content"
TEMPLATE = (ROOT / "templates" / "page.html").read_text(encoding="utf-8")
TODAY = datetime.date.today().isoformat()

ORG = {
    "@context": "https://schema.org", "@type": "ProfessionalService",
    "@id": SITE + "/#organization", "name": "Tendering.me",
    "legalName": "Fidelity Consulting d.o.o.", "url": SITE + "/",
    "image": SITE + "/og-image.png", "telephone": "+382 67 525 774",
    "email": "office@fidelityconsulting.me",
    "address": {"@type": "PostalAddress", "addressLocality": "Podgorica", "addressCountry": "ME"},
    "areaServed": {"@type": "Country", "name": "Montenegro"},
    "founder": {"@type": "Person", "name": "Miloš Vuković", "jobTitle": "Izvršni direktor"},
}

TEMA_OPIS = {  # /praksa/tema/<slug>/ — naslov i uvod
    "robni-znak": ("Robni znak i „ili ekvivalentno“", "Čl. 88 st. 2–4 ZJN: upućivanje na proizvođača, tip ili model je izuzetak, „ili ekvivalentno“ ne spašava kad se predmet mogao opisati funkcionalno, a kriterijumi ekvivalentnosti su samostalan uslov."),
    "kumulativni-efekat": ("Kumulativni efekat i parametri iz kataloga", "Pojedinačno dopuštene karakteristike koje u kombinaciji ispunjava jedan proizvod. Dokazuje se tabelom proizvođača i, kad je materija stručna, vještačenjem."),
    "autorizacija-proizvodjaca": ("Autorizacija proizvođača", "Zahtjev za autorizaciju „isključivo od proizvođača“ isključuje ovlašćene predstavnike — dosljedno poništavano uz presudu Upravnog suda U.br. 4816/18."),
    "reference-i-proporcionalnost": ("Reference i proporcionalnost", "Čl. 12, 101–102 ZJN: prag referenci mora biti srazmjeran procijenjenoj vrijednosti i stvarnom obimu; Komisija sama poredi."),
    "kriterijumi-vrednovanja": ("Kriterijumi vrednovanja", "Čl. 117–118 ZJN: bodovanje obaveznog zahtjeva ili parametra koji ima jedan proizvođač je nezakonito — najstabilnije pravilo Komisije."),
    "kompatibilnost": ("Kompatibilnost sa postojećom opremom", "Prihvaćena samo kad su karakteristike postojećeg sistema objavljene i opisane otvorenim standardom."),
    "jasnoca-td": ("Jasnoća i potpunost dokumentacije", "Čl. 86 ZJN: nedostajući predmjer, neobjavljene karakteristike, interne kontradikcije — „siguran“ osnov usvajanja."),
    "pojasnjenje-i-izmjena": ("Pojašnjenje i izmjena dokumentacije", "Čl. 94–95 ZJN: pojašnjenje ne smije mijenjati dokumentaciju; odgovor na predlog nije akt protiv kojeg je žalba dozvoljena."),
    "rok-za-zalbu": ("Rok za žalbu", "Čl. 186 ZJN: teče od objave osnovne dokumentacije; produženje roka nije izmjena; 11. dan je kasno."),
    "naknada": ("Naknada za žalbu", "Čl. 188 ZJN: 1 % po svakoj partiji, najviše 20.000 €, dokaz do isteka roka, povraćaj kad je žalba osnovana."),
    "vjestacenje": ("Vještačenje", "Čl. 194 st. 2 ZJN: Komisija angažuje sudskog vještaka kad su navodi konkretni i stručni — i po pravilu ga u cjelosti prihvata."),
    "rokovi-postupka": ("Rokovi postupka", "Čl. 54 ZJN: skraćeni rok za ponude bez konkretno obrazložene hitnosti je povreda."),
    "esjn": ("ESJN i automatsko otvaranje ponuda", "Ako naručilac poslije žalbe ne zaustavi fazu i ponude se otvore, cijeli postupak se poništava bez ispitivanja merituma."),
}


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit("Nema front mattera")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for k in ("teme", "clanovi"):
        if k in meta:
            meta[k] = [x.strip() for x in meta[k].split(",") if x.strip()]
    return meta, m.group(2)


MAILTO = "mailto:office@fidelityconsulting.me?subject=Tender%20za%20prvu%20%28besplatnu%29%20analizu"


def md(text):
    # Samostalan red "[Tekst dugmeta]" → crveno dugme sa mailto linkom.
    text = re.sub(r"^\[([^\]\n]+)\]\s*(?:·.*)?$",
                  lambda m: f'<a class="btn btn-red" href="{MAILTO}">{m.group(1)}</a>', text, flags=re.M)
    h = markdown.markdown(text, extensions=["tables", "attr_list", "md_in_html"])
    return h.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")


def breadcrumb(url, title, lang):
    parts = [p for p in url.strip("/").split("/") if p]
    names = {"usluge": "Usluge", "vodic": "Vodiči", "blog": "Blog", "praksa": "Praksa",
             "en": "English", "services": "Services", "guide": "Guides", "tema": "Teme",
             "komisija": "Komisija", "upravni-sud": "Upravni sud", "narucilac": "Naručioci"}
    home = "Home" if lang == "en" else "Početna"
    items = [{"@type": "ListItem", "position": 1, "name": home, "item": SITE + "/"}]
    crumbs = [f'<a href="/{"en/" if lang == "en" else ""}">{home}</a>']
    acc = ""
    for i, p in enumerate(parts):
        acc += "/" + p
        last = i == len(parts) - 1
        name = title if last else names.get(p, p)
        if not last and acc in ("/en/services", "/en/guide", "/praksa/komisija", "/praksa/upravni-sud", "/praksa/tema"):
            continue  # nema hub stranice — ne linkuj i ne stavljaj u schema
        items.append({"@type": "ListItem", "position": len(items) + 1, "name": name, "item": SITE + acc + "/"})
        hub = {"/en/services": "/en/", "/en/guide": "/en/", "/praksa/komisija": "/praksa/",
               "/praksa/upravni-sud": "/praksa/", "/praksa/tema": "/praksa/"}.get(acc, acc + "/")
        crumbs.append(html.escape(name) if last else f'<a href="{hub}">{html.escape(name)}</a>')
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}, " › ".join(crumbs)


def faq_schema(body_html):
    """FAQ blok = <h2>Česta pitanja</h2> praćen <p><strong>Pitanje?</strong> Odgovor</p>."""
    m = re.search(r"<h2[^>]*>(Česta pitanja|FAQ)</h2>(.*?)(?=<h2|\Z)", body_html, re.S)
    if not m:
        return None
    qa = re.findall(r"<p><strong>(.*?)</strong>\s*(.*?)</p>", m.group(2), re.S)
    if not qa:
        return None
    strip = lambda s: re.sub(r"<[^>]+>", "", s).strip()
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": strip(q),
                            "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in qa]}


def render(meta, body_md, extra_schema=None):
    lang = meta.get("lang", "me")
    url = meta["url"]
    body_html = md(body_md)
    bc_schema, bc_html = breadcrumb(url, meta["title"], lang)
    schemas = [ORG, bc_schema]
    if meta.get("type") in ("vodic", "blog", "praksa", "guide"):
        schemas.append({
            "@context": "https://schema.org", "@type": "Article",
            "headline": meta["title"], "description": meta["description"],
            "inLanguage": "en" if lang == "en" else "sr-Latn-ME",
            "datePublished": meta.get("date", TODAY), "dateModified": meta.get("modified", meta.get("date", TODAY)),
            "author": {"@type": "Person", "name": "Miloš Vuković", "url": SITE + "/o-nama/"},
            "publisher": {"@id": SITE + "/#organization"},
            "mainEntityOfPage": SITE + url, "image": SITE + "/og-image.png",
        })
    fs = faq_schema(body_html)
    if fs:
        schemas.append(fs)
    if extra_schema:
        schemas.append(extra_schema)

    hreflang = ""
    if meta.get("alt"):
        me_url, en_url = (url, meta["alt"]) if lang != "en" else (meta["alt"], url)
        hreflang = (f'<link rel="alternate" hreflang="sr-Latn-ME" href="{SITE}{me_url}">\n'
                    f'<link rel="alternate" hreflang="en" href="{SITE}{en_url}">\n'
                    f'<link rel="alternate" hreflang="x-default" href="{SITE}{me_url}">')

    cta = (("Send us a tender — first review free", "Document within 24 hours.")
           if lang == "en" else ("Pošaljite nam tender — prva analiza besplatna", "Dokument za 24 sata."))
    out = TEMPLATE
    for k, v in {
        "LANG": "en" if lang == "en" else "sr-Latn-ME",
        "TITLE": html.escape(meta["title"] + (" | Tendering.me" if len(meta["title"]) < 45 else "")),
        "DESCRIPTION": html.escape(meta["description"]),
        "CANONICAL": SITE + url, "HREFLANG": hreflang,
        "OG_LOCALE": "en_US" if lang == "en" else "sr_ME",
        "SCHEMA": "\n".join(f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>' for s in schemas),
        "BREADCRUMB": bc_html, "BODY": body_html,
        "CTA_TITLE": cta[0], "CTA_SUB": cta[1],
        "NAV_HOME": "/en/" if lang == "en" else "/",
        "NAV": (('<a href="/en/services/tender-appeal-montenegro/">Appeals</a><a href="/en/guide/montenegro-public-procurement-law/">Guide</a><a href="/en/pricing/">Pricing</a><a href="/">ME</a>')
                if lang == "en" else
                '<a href="/usluge/">Usluge</a><a href="/vodic/">Vodiči</a><a href="/praksa/">Praksa</a><a href="/blog/">Blog</a><a href="/cijene/">Cijene</a><a href="/en/">EN</a>'),
        "YEAR": str(datetime.date.today().year),
    }.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def write(url, html_text):
    p = ROOT / url.strip("/") / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_text, encoding="utf-8")
    return url


def build_pages():
    urls = []
    praksa = []
    for f in sorted(CONTENT.rglob("*.md")):
        meta, body = front_matter(f.read_text(encoding="utf-8"))
        if meta.get("type") == "praksa":
            meta["_body"] = body
            praksa.append(meta)
        urls.append(write(meta["url"], render(meta, body)))
    return urls, praksa


def build_praksa(entries):
    """/praksa/ hub + /praksa/tema/<slug>/ iz front mattera rješenja."""
    urls = []
    if not entries:
        return urls
    entries.sort(key=lambda e: e.get("datum", ""), reverse=True)

    def row(e):
        ishod = e.get("ishod", "")
        return (f'<tr><td><a href="{e["url"]}">{html.escape(e["broj"])}</a></td>'
                f'<td>{html.escape(e.get("narucilac", ""))}</td><td>{html.escape(e.get("predmet", ""))}</td>'
                f'<td>{html.escape(e.get("datum", ""))}</td><td>{html.escape(ishod)}</td></tr>')

    table = lambda es: ('<table><thead><tr><th>Broj</th><th>Naručilac</th><th>Predmet</th><th>Datum</th><th>Ishod</th></tr></thead><tbody>'
                        + "".join(row(e) for e in es) + "</tbody></table>")

    teme = {}
    for e in entries:
        for t in e.get("teme", []):
            teme.setdefault(t, []).append(e)

    tema_links = "".join(f'<li><a href="/praksa/tema/{t}/">{html.escape(TEMA_OPIS.get(t, (t, ""))[0])}</a> ({len(es)})</li>'
                         for t, es in sorted(teme.items()))
    hub = {"url": "/praksa/", "lang": "me", "title": "Praksa Komisije za zaštitu prava i Upravnog suda",
           "description": f"Rješenja Komisije za zaštitu prava i presude Upravnog suda, sažeta i objašnjena — {len(entries)} odluka po temama: robni znak, kumulativni efekat, reference, rokovi."}
    hub_body = (f"# Praksa: rješenja Komisije i presude Upravnog suda\n\n"
                f"Svako rješenje sažeto u pet rečenica, sa članovima ZJN, ishodom i onim što znači za ponuđača. "
                f"Sažeci su naša analiza — prije citiranja u podnesku provjerite tekst u izvornoj odluci.\n\n"
                f"## Po temama\n\n<ul>{tema_links}</ul>\n\n## Sva rješenja ({len(entries)})\n\n{table(entries)}\n")
    urls.append(write("/praksa/", render(hub, hub_body)))

    for t, es in teme.items():
        naslov, uvod = TEMA_OPIS.get(t, (t, ""))
        meta = {"url": f"/praksa/tema/{t}/", "lang": "me", "title": f"Praksa: {naslov}",
                "description": (uvod[:150] + "…") if len(uvod) > 150 else uvod}
        body = f"# {naslov}\n\n{uvod}\n\n## Rješenja ({len(es)})\n\n{table(es)}\n\n[Sva praksa →](/praksa/)\n"
        urls.append(write(meta["url"], render(meta, body)))
    return urls


def build_en_home():
    """en/index.html iz index.html: EN head + podrazumijevani jezik."""
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    head_me = re.search(r"<!-- SEO:START -->.*?<!-- SEO:END -->", src, re.S).group(0)
    head_en = (ROOT / "templates" / "head-en.html").read_text(encoding="utf-8")
    out = src.replace(head_me, head_en)
    out = out.replace('<html lang="sr-Latn-ME" data-lang="me">', '<html lang="en" data-lang="en">')
    (ROOT / "en").mkdir(exist_ok=True)
    (ROOT / "en" / "index.html").write_text(out, encoding="utf-8")
    return "/en/"


def build_sitemap(urls):
    rows = "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in ["/"] + urls)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + "</urlset>\n",
        encoding="utf-8")


if __name__ == "__main__":
    urls, praksa = build_pages()
    urls += build_praksa(praksa)
    urls.append(build_en_home())
    build_sitemap(sorted(set(urls)))
    print(f"OK — {len(urls) + 1} stranica, sitemap.xml ažuriran.")
