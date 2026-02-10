# landing_page_filter.py

## Summary

A specialized filtering module designed to detect corporate landing pages, e-commerce sites, and spam services.

## Description

`landing_page_filter.py` provides targeted heuristic checks that complement the broader quality filters. It focuses on structural patterns and vocabulary common in "commercial" web pages as opposed to "content" or "article" pages.

### Key Detection Logic:

- **Service Landing Pages**: Looks for high concentrations of commercial keywords (pricing, product, solution) and call-to-action (CTA) buttons.
- **E-commerce**: Detects shopping carts, "Add to Cart" buttons, and currency/billing vocabulary.
- **Spam Services**: Scans for specific shady service keywords (SEO boosting, cheap followers, etc.).
- **Homepage Non-Articles**: Identifies if a URL is a domain root and lacks the complexity or keyword density of a blog post.

## Public API / Interfaces

### `is_service_landing_page(html, text, url_path)`

Returns a boolean and a score indicating if the page is likely a corporate service page.

### `is_ecommerce_page(html)`

Returns boolean true if common e-commerce snippets are found.

### `is_homepage_not_article(url, html)`

Checks if a homepage is a "static" landing page rather than a hub of content.

### `detect_spam_services(url, text)`

Boolean check for specific spammy industry keywords.

## Dependencies

- `BeautifulSoup` (bs4): For structural HTML analysis.
- `lxml`: Used as the parser for speed.

## Notes/Limitations

- These filters are "hard" rejections in `quality_filter.py`, meaning if they trigger, the page is discarded before the unified score is even calculated.

## Related

- [quality_filter-py.md](quality_filter-py.md)
- [quality_config-py.md](quality_config-py.md)
