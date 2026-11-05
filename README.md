# NFL Deadline Command — 2026

## What is included

- `index.html` — polished responsive standalone HTML dashboard with sticky countdown to **Nov 10, 2026 at 4 PM New York time**, built-in verified trade snapshot, team logos, player cards, pick breakdowns, grades, filters, detail popups, and sharing controls.
- `server.py` — optional Flask host with a server-side seven-minute news-source check, ESPN roster-profile enrichment, and `/api/trades` endpoint.
- `trades.json` — editable seed records for seven confirmed trades plus one reported agreement, as verified Nov 5, 2026.
- `render.yaml`, `requirements.txt` — basic one-click-compatible Render deployment configuration.

## Run on your computer

1. Install Python 3.10+.
2. In this folder, run `pip install -r requirements.txt`.
3. Run `python server.py`.
4. Visit `http://localhost:5000`.

## Make it shareable

Push the contents of this folder to a GitHub repository, create a Render Web Service from the repo, and deploy using the included `render.yaml`. Send people the resulting Render URL. The server must be running for live source polling; uploading `index.html` alone to GitHub Pages or Netlify shows the built-in snapshot, not live transaction sync.

## Important data limitations

- An HTML-only page cannot reliably pull ESPN and CBS article content because browser cross-origin restrictions and publisher anti-bot controls can block requests. The included Python server performs checks. Hosting is **not configured/deployed automatically**.
- Every page view requests the backend; the backend throttles news checks to once every **420 seconds**. The page itself re-requests every seven minutes while open. This is polling, not immediate push updates. Sources can block scraping, change formatting, or omit transactions; 100% coverage is not guaranteed.
- The backend currently detects new **fully parseable** trades on the official NFL tracker. Deals lacking identifiable recipients, complete packages, or dates may require manually editing `trades.json`. CBS serves as a reachability/cross-check source, not an independent parsed trade feed. The user-facing status distinguishes source success from fallback mode.
- Player profile enrichment uses public, undocumented ESPN roster JSON. If unavailable, known profile information in the HTML or explicit “awaiting data” placeholders remain visible. Position-specific 2026 stats are included as a checked Nov 5 reference snapshot where available, but are not a live statistics feed. Offensive linemen show games and games started; this is not a blocking-efficiency measure. No fake stats are generated.
- Draft round and year are not the same as exact overall pick position: 2027/2028 exact slots are **not known** yet. Popups show what each club obtained in the depicted transaction, not complete team draft inventories.
- Grades are CBS Sports **editorial grades**, and the winner indication is a comparison of those grades. It is not a proprietary objective valuation algorithm.
- The source trackers conflicted on the sixth/seventh-round pieces in the Marvin Harrison Jr. trade; the NFL.com package is used in the provided snapshot. The Brissett move was a reported agreement with compensation TBD as of Nov 5.
- CSS and fonts are delivered from internet providers; profile and team images use ESPN CDN. Team logos and player likenesses are owned by their respective rights holders. This is an unofficial fan project.

## Data maintenance

To add or fix a transaction, edit `trades.json` and redeploy. Receives are keyed by NFL team abbreviation, with entries of type `player`, `pick`, or `unknown`. Each trade must have two team codes, a date, status, and sources.
