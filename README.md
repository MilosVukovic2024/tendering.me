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
assets/fonts/              Archivo (varijabilni woff2, latin + latin-ext; licenca OFL.txt)
assets/fonts.css           @font-face — build.py ga umeće inline u <head> (šablon: {{FONTS}}, index.html: FONTS markeri)
assets/motion.css, .js     animacije (vidi „Animacije”) — CSS inline ({{MOTION}} / MOTION markeri), JS kao fajl
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

## Animacije

Jedan izvor: `assets/motion.css` (build ga umeće inline) i `assets/motion.js` (`defer`, `?v=<hash>`; build odbija > 15 kB gzip).
Strane samo koriste klase; bez JS-a i pod `prefers-reduced-motion` sve je odmah vidljivo.

| Klasa | Šta radi |
|---|---|
| `a-hero` | grupa koja ulazi pri učitavanju: `.a-line` redovi naslova (80 ms razmak, samo pomak — LCP), zatim `.a-after` (+150 ms; `--a-base`, `--ai`) |
| `a-group` | isto kao hero, ali kad uđe u vidno polje (npr. završni poziv) |
| `a-reveal` | element ulazi pomakom 16 px + opacity, jednom |
| `a-stagger` | djeca ulaze u nizu, 60 ms (najviše 6 koraka) |
| `a-count` | brojač 0 → vrijednost, 1,2 s; `data-to`, `data-dec`, `data-prefix`, `data-suffix`; tekst u HTML-u je konačna vrijednost |
| `a-card`, `a-card-media` | hover: ivica u akcentu, podizanje 2 px (ili pomak ilustracije 4 px) |
| `a-steps` | linija napretka uz korake (`.step-card` ili `li`); `--a-line-x` = položaj linije |
| `a-sheen` | jednokratan sjaj po gornjoj ivici kad roditelj uđe u vidno polje |
| `a-navlink`, `a-bar`, `a-menu` + `data-menu-toggle` | podvlaka linka; traka sa zamućenjem poslije 8 px; mobilni meni |
| `a-btn` | dugme (pozadina 150 ms, pritisak 0.98) — `.btn*` i `.tab-btn` ga već imaju |

Markdown strane: `MOTION_KIND` u build.py daje `<article data-motion="flow">` (sekcije h2 ulaze pri skrolu) ili `"longread"`
(samo naslov + linija napretka čitanja; tekst se ne animira). Korake u markdownu označi omotačem
`<div class="a-steps" markdown="1"> … </div>`. Fajlovi u `assets/` se keširaju godinu dana (vercel.json) — fontovima mijenjaj ime ako se promijene.

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
