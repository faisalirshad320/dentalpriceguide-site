# dentalpriceguide.com

Static site: US dental procedure costs from published claims and survey data, medically reviewed by Dr. Faisal Irshad, MBBS.

- Generator: `_src/build.py` (blocked from the web by `.htaccess` and `robots.txt`).
- Page specs: `_src/content/<slug>.json`, written by the article machine (`generate-dental.js`, Anthropic API credits).
- Live pages: `_src/data/publish.json`. Everything in `_src/data/pages-index.json` that is not in it is queued.
- `python3 _src/build.py` builds into the repo root; `--release N` publishes the next N queued pages; `--status` shows counts.
- `.github/workflows/daily-release.yml` releases 3 pages/day at 06:30 PKT, commits, pings IndexNow.
- Hosting: Cloudways server 1638726, app 6739640, git-deployed from `main` into public_html.
