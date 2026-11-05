# NFL Deadline Command — auto-sync upgrade

This is an **upgrade for your already-running GitHub + Render website**, not a new website. Keep the same GitHub repository and Render URL.

## Upload the updated files
1. Unzip this package locally.
2. In your **existing GitHub repository**, upload `server.py`, `sync_trades.py`, `index.html`, `trades.json`, `README.md`, `requirements.txt`, and `render.yaml` directly to the repository root. Confirm replacements and commit.
3. To upload the hidden `.github/workflows/refresh-trades.yml` file, the easiest GitHub browser approach is: **Add file → Create new file**, enter `.github/workflows/refresh-trades.yml` in the filename field, paste the contents from this package, and commit. Alternatively upload the `.github` folder from an extracted copy, ensuring your file explorer shows hidden directories.
4. In GitHub: **Settings → Actions → General → Workflow permissions**, select **Read and write permissions** if editable; save. If your organization blocks this option, a repository admin must allow it.
5. GitHub: **Actions → Refresh confirmed NFL trades → Run workflow**. Review the run's result.
6. Render will normally redeploy when GitHub files change. Check Render's **Events / Logs** for a successful deploy, then refresh your existing public URL.

## How updates operate
- GitHub Actions is scheduled every **10 minutes**, **best-effort** (GitHub may delay scheduled jobs). It fetches the NFL.com tracker, parses an exact *date + 2 teams + complete incoming packages* and only commits when it finds a new completed deal or an existing agreement is confirmed. It does not invent exact times or draft pick numbers.
- The existing Render API also checks while the site is visited (throttled to seven minutes); those in-memory updates can be lost when Render Free sleeps. The GitHub Actions file provides persistent changes through Git commits.
- GitHub Actions can be skipped or delayed, and sports sites can block automated fetches or change HTML. **This is not a guarantee of 100% coverage**, and new trades without a complete package or official NFL entry will not appear immediately. Inspect the Actions log if it reports an error; the existing verified data remains available.
- ESPN enrichment is via an unofficial roster endpoint and may be incomplete. 2026 position stats on the page are still a dated snapshot, **not live player stats**. CBS is linked for corroboration/editorial grades; automatic CBS trade parsing and grade extraction are not implemented.

## What to test
- The current Render URL and `/api/health` should load.
- GitHub Actions tab should show the `Refresh confirmed NFL trades` workflow. Manually trigger it and inspect its log. If it says the site couldn't be parsed, no trade data is overwritten.
- `trades.json` in GitHub gains a new commit **only when newly confirmed official trades are detected**, not every ten minutes.

## Source
- Official transactions: https://www.nfl.com/news/nfl-trade-deadline-track-every-move-since-start-of-2026-regular-season
- Other info / grades for review: https://www.cbssports.com/nfl/news/2026-nfl-trade-deadline-tracker-latest-deals-grades/

The tracker is an unofficial fan project, not affiliated with the NFL, ESPN, or CBS Sports.
