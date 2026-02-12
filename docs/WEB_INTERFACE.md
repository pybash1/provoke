# Web App (`provoke/web/app.py`)

## Summary

The main Flask web application for the Provoke Search Engine. It provides a search interface, an admin dashboard for monitoring crawl stats, and tools for managing domain blacklists/whitelists and labeling data.

## Description

`provoke/web/app.py` serves as the front-end and administrative hub. It integrates with the `SearchEngine` from `provoke.indexer` for search functionality and interacts directly with `index.db` to manage pages and domain lists. The admin dashboard provides real-time insights into indexed pages, rejection statistics, and labeling progress.

### Flow:

1.  **Search**: Users can query the `SearchEngine` through the root route.
2.  **Admin Dashboard**: Accessible at `/admin`, it aggregates data from the database and local CSV logs to show performance metrics.
3.  **Domain Management**: Routes for adding/removing domains from blacklists and whitelists.
4.  **Crawl Interface**: Allows starting a crawl for a specific URL directly from the browser, streaming the logs back to the user.
5.  **Labeling UI**: A dedicated interface for reviewing URLs and assigning quality labels (good/bad/unsure), which are saved to `data/to_label.csv`.

## Public API / Interfaces

### Web Routes:

- `GET /`: Search index page.
- `GET /admin`: Main administrator dashboard.
- `GET /domains`: View indexed pages grouped by domain. Features a scrollable sidebar with custom scrollbar styling.
- `GET /admin/lists`: Manage blacklist and whitelist domains.
- `GET /admin/label`: UI for manual data labeling.
- `GET /admin/crawl`: Trigger a crawl (supports `url` and `depth` parameters).
- `GET /admin/test_url`: Dry-run quality evaluation for a specific URL using `config.evaluate_page_quality`.
- `GET /admin/manual_insert`: Manual page insertion UI. Allows bypassing all quality filters to directly index a page.

### Manual Insert Behavior

The manual insert feature (`/admin/manual_insert`) allows administrators to force-index a page that would normally be rejected by quality filters:

1. Fetches the URL and extracts title/content
2. Runs ML classification as a warning (if ML is enabled and the page is classified as "bad" with confidence above the `low_confidence_threshold` from `config.ML_CONFIG`, default 0.3)
3. On confirmation, saves to database with:
   - `quality_score`: Set to `0` (integer)
   - `quality_tier`: Set to `"manual"` to distinguish from crawled content

### Internal Functions:

- `get_lists()`: Fetches blacklisted and whitelisted domains from the DB.
- `get_admin_data()`: Aggregates statistics for the dashboard.
- `get_domain_info(target_domain)`: Retrieves page data for specific domains.

## Dependencies

- `Flask`: Web framework.
- `sqlite3`: Database interaction.
- `provoke.indexer.SearchEngine`: Core search functionality.
- `provoke.config`: Central configuration & quality logic.
- `BeautifulSoup`: For basic HTML parsing in dry-runs.
- `requests`: For fetching URLs in dry-runs.
- `subprocess`: For running the crawler from the UI.

## Examples

To run the web app:

```bash
uv run python provoke/web/app.py
```

By default, it runs on `http://127.0.0.1:4000`.

## UI Styling

The web interface uses Tailwind CSS with a custom dark theme:

- **Color Scheme**: Dark background (`#0a0a0c`), surface cards (`#121217`), and accent colors (indigo primary, pink secondary).
- **Typography**: JetBrains Mono font family for a technical aesthetic.
- **Custom Scrollbars**: The domains page sidebar (`/domains`) features custom-styled scrollbars with semi-transparent white thumbs on WebKit browsers and Firefox-compatible scrollbar colors.

## Notes/Limitations

- The `admin_crawl` route uses `subprocess` to run `crawler.py` and streams output. Ensure the environment has the necessary permissions.
- Labeling updates are written directly to `data/to_label.csv`.
- The `/domains` page features a custom-styled scrollbar for the domain sidebar using CSS (WebKit and Firefox compatible).

## Suggested Tests

- Verify search results appear for known keywords.
- Test adding a domain to the blacklist and ensure it's reflected in the dashboard.
- Verify the labeling UI correctly updates the CSV.
- Test the manual insert feature:
  - Insert a URL that would normally be rejected
  - Confirm the warning appears when ML flags it as low quality
  - Verify the page is saved with `quality_score=0` and `quality_tier="manual"`

## Related

- [CONFIG.md](CONFIG.md)
- [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
- [SEARCH_ENGINE.md](SEARCH_ENGINE.md)
