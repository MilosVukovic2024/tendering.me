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
import json, re, html, datetime, gzip, hashlib
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
SITE = "https://www.tendering.me"
CONTENT = ROOT / "content"
TEMPLATE = (ROOT / "templates" / "page.html").read_text(encoding="utf-8")
TODAY = datetime.date.today().isoformat()

ORG = {
    "@context": "https://schema.org", "@type": "ProfessionalService",
    "@id": SITE + "/#organization", "name": "Tendering.me",
    "legalName": "Fidelity Consulting d.o.o.", "url": SITE + "/",
    "image": SITE + "/og-image.png", "telephone": "+382 67 525 774",
    "email": "tendering@fidelityconsulting.me",
    "address": {"@type": "PostalAddress", "streetAddress": "Baku 5", "postalCode": "81000", "addressLocality": "Podgorica", "addressCountry": "ME"},
    "vatID": "02822199",
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


ASSETS = ROOT / "assets"


def css_min(css):
    """Bez komentara i suvišnih razmaka — dovoljno za inline <style>."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,])\s*", r"\1", css)
    return re.sub(r":\s+", ":", css).strip()


# Fontovi sa sajta (assets/fonts.css): preload + @font-face inline, bez zahtjeva prema Google Fonts.
FONTS = ("".join(f'<link rel="preload" href="/assets/fonts/{f}" as="font" type="font/woff2" crossorigin>\n'
                 for f in ("archivo-latin.woff2", "archivo-latin-ext.woff2"))
         + "<style>" + css_min((ASSETS / "fonts.css").read_text(encoding="utf-8")) + "</style>")


# Animacije (assets/motion.css + assets/motion.js — jedini izvor): CSS inline, JS sa ?v=<hash> (keš na Vercelu: vercel.json).
# Inline skripta postavlja .js prije prvog prikaza (bez JS-a ništa nije skriveno) i preskače prelaz strane pri skoku na #sidro.
_motion_js = (ASSETS / "motion.js").read_bytes().replace(b"\r\n", b"\n")
MOTION_JS_GZIP = len(gzip.compress(_motion_js, 9))
if MOTION_JS_GZIP > 15000:
    raise SystemExit(f"assets/motion.js: {MOTION_JS_GZIP} B gzip — limit je 15 kB")
MOTION = ('<script>document.documentElement.classList.add("js");addEventListener("pagereveal",function(e){'
          'if(e.viewTransition&&location.hash)e.viewTransition.skipTransition()})</script>\n'
          "<style>" + css_min((ASSETS / "motion.css").read_text(encoding="utf-8")) + "</style>\n"
          f'<script src="/assets/motion.js?v={hashlib.sha256(_motion_js).hexdigest()[:8]}" defer '
          "onerror=\"document.documentElement.classList.remove('js')\"></script>")


def inject(src, name, block, required=True):
    """Zamijeni sadržaj između <!-- NAME:START … --> i <!-- NAME:END --> (najviše jedan par)."""
    pat = re.compile(r"(<!-- " + name + r":START[^>]*-->\n).*?(<!-- " + name + r":END -->)", re.S)
    out, n = pat.subn(lambda m: m.group(1) + block + "\n" + m.group(2), src, count=1)
    if n != 1 and required:
        raise SystemExit(f"index.html: nedostaje marker {name}")
    return out


def build_home_assets():
    """Zajedničke blokove upiši i u index.html (ručno održavanu početnu), prije generisanja /en/."""
    p = ROOT / "index.html"
    src = p.read_text(encoding="utf-8")
    out = inject(inject(src, "FONTS", FONTS), "MOTION", MOTION, required=False)
    if out != src:
        p.write_text(out, encoding="utf-8")


MAILTO = "mailto:tendering@fidelityconsulting.me?subject=Tender%20za%20prvu%20%28besplatnu%29%20analizu"


def md(text):
    # Samostalan red "[Tekst dugmeta]" → crveno dugme sa mailto linkom.
    text = re.sub(r"^\[([^\]\n]+)\]\s*(?:·.*)?$",
                  lambda m: f'<a class="btn btn-red" href="{MAILTO}">{m.group(1)}</a>', text, flags=re.M)
    h = markdown.markdown(text, extensions=["tables", "attr_list", "md_in_html"])
    return h.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")


def breadcrumb(url, title, lang):
    parts = [p for p in url.strip("/").split("/") if p]
    names = {"usluge": "Usluge", "vodic": "Vodiči", "primjeri": "Primjeri iz prakse", "blog": "Blog", "praksa": "Praksa",
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


# Profil animacije po šablonu (vidi assets/motion.css): "flow" — sekcije ulaze pri skrolu; "longread" — samo naslov
# i linija napretka čitanja, tekst se ne animira. Ključ je type iz front mattera ili URL; strana bez profila nema animaciju sadržaja.
MOTION_KIND = {"usluga": "flow", "vodic": "longread", "guide": "longread", "blog": "longread", "praksa": "longread"}


def motion_kind(meta):
    return MOTION_KIND.get(meta["url"]) or MOTION_KIND.get(meta.get("type", ""))


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

    kind = motion_kind(meta)
    cta = (("Send us a tender — first review free", "Document within 24 hours.")
           if lang == "en" else ("Pošaljite nam tender — prva analiza besplatna", "Dokument za 24 sata."))
    out = TEMPLATE
    for k, v in {
        "LANG": "en" if lang == "en" else "sr-Latn-ME",
        "TITLE": html.escape(meta["title"] + (" | Tendering.me" if len(meta["title"]) < 45 else "")),
        "DESCRIPTION": html.escape(meta["description"]),
        "CANONICAL": SITE + url, "HREFLANG": hreflang, "FONTS": FONTS, "MOTION": MOTION,
        "ARTICLE_ATTR": f' data-motion="{kind}"' if kind else "",
        "PROGRESS": '<div class="a-progress" aria-hidden="true"></div>' if kind == "longread" else "",
        "OG_LOCALE": "en_US" if lang == "en" else "sr_ME",
        "SCHEMA": "\n".join(f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>' for s in schemas),
        "BREADCRUMB": bc_html, "BODY": body_html,
        "CTA_TITLE": cta[0], "CTA_SUB": cta[1],
        "NAV_HOME": "/en/" if lang == "en" else "/",
        "NAV": (('<a class="a-navlink" href="/en/services/tender-appeal-montenegro/">Appeals</a><a class="a-navlink" href="/en/guide/montenegro-public-procurement-law/">Guide</a><a class="a-navlink" href="/en/pricing/">Pricing</a><a class="a-navlink" href="/">ME</a>')
                if lang == "en" else
                '<a class="a-navlink" href="/#postupak">10 koraka javne nabavke</a><a class="a-navlink" href="/za-narucioce/">Za naručioce</a><a class="a-navlink" href="/primjeri/">Primjeri iz prakse</a><a class="a-navlink" href="/vodic/">Vodiči</a><a class="a-navlink" href="/cijene/">Cijene</a><a class="a-navlink" href="/en/">EN</a>'),
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


def en_texts(src):
    """Engleski tekstovi iz skripte početne: T.en (rječnik), STEPS.en, PLANS.en — isti izvor koji koristi JS."""
    js = src[src.rindex("<script>"):]
    t_block = re.search(r"const T = \{.*?\n  en: \{(.*?)\n  \}\n\};", js, re.S).group(1)
    t = {k: json.loads('"' + v + '"') for k, v in re.findall(r'(\w+): "((?:[^"\\]|\\.)*)"', t_block)}
    steps = json.loads(re.search(r"const STEPS = \{.*?\n  en: (\[.*?\])\n\};", js, re.S).group(1))
    plans = re.search(r"const PLANS = \{.*?\n  en: \{\s*a: (\[.*?\]),\s*b: (\[.*?\])\s*\}", js, re.S)
    return t, steps, (json.loads(plans.group(1)), json.loads(plans.group(2)))


def prerender_en(out):
    """Upiši EN tekst u HTML (/en/ više ne prikazuje crnogorski tekst prije JS-a; nema pomjeranja pri zamjeni).
    JS (renderText, renderSteps, renderPlans) na /en/ i dalje radi isto — samo upisuje iste vrijednosti."""
    t, steps, (plan_a, plan_b) = en_texts(out)
    esc = lambda x: html.escape(x, quote=False)

    def i18n(m):
        key = m.group(3)
        return m.group(1) + esc(t[key]) + m.group(5) if key in t else m.group(0)
    head, sep, script = out.rpartition("<script>")
    head = re.sub(r'(<(\w+)\b[^>]*\bdata-i18n="(\w+)"[^>]*>)([^<]*)(</\2>)', i18n, head)
    # Linkovi koje renderText mijenja na EN
    links = {"navGuides": "/en/guide/montenegro-public-procurement-law/", "navPrice": "/en/pricing/",
             "faq1l": "/en/services/tender-appeal-montenegro/", "faq2l": "/en/services/tender-appeal-montenegro/",
             "faq3l": "/en/guide/montenegro-public-procurement-law/"}
    for key, href in links.items():
        head, n = re.subn(r'<a\b[^>]*\bdata-i18n="' + key + r'"[^>]*>',
                          lambda m: re.sub(r'href="[^"]*"', 'href="' + href + '"', m.group(0)), head)
        if n != 1:
            raise SystemExit(f"index.html: link {key} nije pronađen")
    # Dugme demoa, statične kartice koraka i stavke paketa
    for phase, key in (("idle", "scanIdle"), ("scanning", "scanRunning"), ("done", "scanDone")):
        head = head.replace(f'<span data-l="{phase}">' + re.search(f'<span data-l="{phase}">([^<]*)<', head).group(1),
                            f'<span data-l="{phase}">' + esc(t[key]), 1)
    grid = re.search(r'(<div id="steps-grid"[^>]*>)(.*?)(</div>\n      </div>)', head, re.S)
    cards = grid.group(2)
    for tag, idx in (("h3", 0), ("p", 1)):
        vals = iter(steps)
        cards = re.sub(rf"(<{tag}\b[^>]*>)[^<]*(</{tag}>)", lambda m: m.group(1) + esc(next(vals)[idx]) + m.group(2), cards)
    vals = iter(steps)
    cards = re.sub(r'(<div style="margin-top:auto;[^"]*">)[^<]*(</div>)', lambda m: m.group(1) + esc(next(vals)[2]) + m.group(2), cards)
    head = head[:grid.start(2)] + cards + head[grid.end(2):]
    for list_id, items in (("planA-list", plan_a), ("planB-list", plan_b)):
        m = re.search(rf'(<div id="{list_id}"[^>]*>)(.*?)(</div></div>)', head)
        row = re.search(r'<div style="[^"]*">', m.group(2)).group(0)
        head = head[:m.start(2)] + "".join(row + esc(x) + "</div>" for x in items[:-1]) + row + esc(items[-1]) + head[m.end(2):]
    # Brojke u engleskom formatu (4,800+)
    head = re.sub(r'(class="a-count" data-to="(\d{4,})"[^>]*>)(\d{1,3})\.(\d{3})',
                  lambda m: m.group(1) + m.group(3) + "," + m.group(4), head)
    return head + sep + script


def build_en_home():
    """en/index.html iz index.html: EN head, podrazumijevani jezik i engleski tekst upisan u HTML."""
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    head_me = re.search(r"<!-- SEO:START -->.*?<!-- SEO:END -->", src, re.S).group(0)
    head_en = (ROOT / "templates" / "head-en.html").read_text(encoding="utf-8")
    out = src.replace(head_me, head_en)
    out = out.replace('<html lang="sr-Latn-ME" data-lang="me">', '<html lang="en" data-lang="en">')
    if out.count('data-lang="en"') != 1:
        raise SystemExit("index.html: <html lang=… data-lang=…> nije u očekivanom obliku")
    out = prerender_en(out)
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
    build_home_assets()
    urls.append(build_en_home())
    build_sitemap(sorted(set(urls)))
    print(f"OK — {len(urls) + 1} stranica, sitemap.xml ažuriran.")
