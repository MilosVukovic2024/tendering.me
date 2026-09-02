# Tendering.me

Landing page for **Tendering.me** — AI forenzika javnih nabavki u Crnoj Gori (Fidelity Consulting d.o.o., Podgorica).

Single static HTML file. No build step, no dependencies, no tracking.

## Structure

```
index.html   — the whole site (HTML + CSS + 10 lines of JS)
.nojekyll    — tells GitHub Pages to serve files as-is
```

## Run locally

Open `index.html` in a browser, or:

```sh
python3 -m http.server 8000
# → http://localhost:8000
```

## Deploy (GitHub Pages)

1. Push to GitHub.
2. **Settings → Pages → Source: Deploy from a branch → `main` / `/ (root)`**.
3. For the custom domain, add a `CNAME` file containing `tendering.me` and point DNS at GitHub Pages.

## Editing

Everything lives in `index.html`:

- Copy and steps — the `<section>` blocks.
- Prices — the `.price` cards in the *Cijene* section; the `mailto:` links carry the package name and price in the subject/body, update both.
- Colours and type — CSS variables in `:root`.

## Contact

office@fidelityconsulting.me · 067 525 774
