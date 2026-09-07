# Tendering.me

Sajt za **Tendering.me** — forenzika javnih nabavki u Crnoj Gori (Fidelity Consulting d.o.o., Podgorica).

Statički HTML, hostovan na Vercelu. Vercel ne pokreće build — generisani HTML se commituje.

## Struktura

```
index.html                 ME početna (ručno se održava; SEO blok između <!-- SEO:START --> i <!-- SEO:END -->)
en/index.html              generiše build.py iz index.html (EN head iz templates/head-en.html)
content/**/*.md            sve ostale stranice: front matter + Markdown
templates/page.html        šablon za content stranice
templates/head-en.html     <head> za EN početnu
build.py                   md → HTML, sitemap.xml, /praksa/ hub i tema-stranice
vercel.json                trailingSlash, (tendering.me → www radi Vercel)
robots.txt, sitemap.xml
usluge/ vodic/ blog/ praksa/ cijene/ o-nama/ en/   ← GENERISANO, ne uređivati ručno
```

## Rad

```
pip install markdown          # jednom
python3 build.py              # prije svakog commita
python3 -m http.server 8000   # http://localhost:8000
git add -A && git commit -m "..." && git push
```

## Nova stranica

Napravi `content/<sekcija>/<ime>.md`:

```
---
url: /vodic/kako-se-zaliti-na-tender/
lang: me                      # ili en
type: vodic                   # usluga | vodic | blog | page | guide | praksa
title: Kako se žaliti na tender u CG      # ≤ 60 znakova
description: ...                            # ≤ 160 znakova
date: 2026-09-15              # za vodic/blog/praksa (Article schema)
alt: /en/guide/...            # opciono: URL parnjaka na drugom jeziku (hreflang)
---

# H1 stranice

Tekst. Samostalan red `[Pošaljite tender — prva analiza besplatna]` postaje crveno mailto dugme.
Blok `## Česta pitanja` sa `**Pitanje?** Odgovor` pasusima automatski dobija FAQ schema.
```

## Rješenje Komisije (/praksa/)

`content/praksa/<broj>.md` sa dodatnim poljima — build pravi `/praksa/`, `/praksa/tema/<slug>/` i tabele sam:

```
type: praksa
url: /praksa/komisija/up-0907-257-2025/
broj: UP.0907-257/2025
narucilac: Montefarm
predmet: Endoproteze kuka
datum: 2025-12-29
ishod: Usvojena — TD poništena
clanovi: čl. 88 st. 1–2, čl. 54 st. 5
teme: kumulativni-efekat, vjestacenje, rokovi-postupka     # slugovi iz TEMA_OPIS u build.py
```

## Kontakt

tendering@fidelityconsulting.me · 067 525 774
