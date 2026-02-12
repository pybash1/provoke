# Web App (`app.py`)

## Summary

The main Flask web application for the Provoke Search Engine. It provides a search interface, an admin dashboard for monitoring crawl stats, and tools for managing domain blacklists/whitelists and labeling data.

## Description

`app.py` serves as the front-end and administrative hub. It integrates with the `SearchEngine` from `indexer.py` for search functionality and interacts directly with `index.db` to manage pages and domain lists. The admin dashboard provides real-time insights into indexed pages, rejection statistics, and labeling progress.

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
- `GET /domains`: View indexed pages grouped by domain.
- `GET /admin/lists`: Manage blacklist and whitelist domains.
- `GET /admin/label`: UI for manual data labeling.
- `GET /admin/crawl`: Trigger a crawl (supports `url` and `depth` parameters).
- `GET /admin/test_url`: Dry-run quality evaluation for a specific URL using `config.evaluate_page_quality`.

### Internal Functions:

- `get_lists()`: Fetches blacklisted and whitelisted domains from the DB.
- `get_admin_data()`: Aggregates statistics for the dashboard.
- `get_domain_info(target_domain)`: Retrieves page data for specific domains.

## Dependencies

- `Flask`: Web framework.
- `sqlite3`: Database interaction.
- `indexer.SearchEngine`: Core search functionality.
- `config`: Central configuration & quality logic.
- `BeautifulSoup`: For basic HTML parsing in dry-runs.
- `requests`: For fetching URLs in dry-runs.
- `subprocess`: For running the crawler from the UI.

## Examples

To run the web app:

```bash
uv run python app.py
```

By default, it runs on `http://127.0.0.1:4000`.

## Notes/Limitations

- The `admin_crawl` route uses `subprocess` to run `crawler.py` and streams output. Ensure the environment has the necessary permissions.
- Labeling updates are written directly to `data/to_label.csv`.

## Suggested Tests

- Verify search results appear for known keywords.
- Test adding a domain to the blacklist and ensure it's reflected in the dashboard.
- Verify the labeling UI correctly updates the CSV.

## Related

- [CONFIG.md](CONFIG.md)
- [CRAWLING_SYSTEM.md](CRAWLING_SYSTEM.md)
- [SEARCH_ENGINE.md](SEARCH_ENGINE.md)
