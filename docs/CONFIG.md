# Configuration & Core Logic (`config.py`)

## Summary

`config.py` is the central nervous system of the Provoke Search Engine. It consolidates all application settings, thresholds, and core quality assessment logic into a single module.

## Description

This module serves two primary purposes:

1.  **Configuration**: Storing constants, environment variable overrides, and tuning parameters.
2.  **Logic**: Implementing the heuristic algorithms for quality scoring, ad detection, and corporate filtering.

## Configuration Sections

### Environment & Server

- **`ENV`**: toggles between `development` (debug mode) and `production` (optimized).
- **`DATABASE_PATH`**: Location of the SQLite database (`index.db`).
- **`SERVER_PORT`**: Port for the Flask web interface (default: 4000).

### Thresholds (`THRESHOLDS`)

Critical numeric limits that determine what gets indexed:

- **`min_words`** (100): Minimum word count for a valid article.
- **`max_words`** (8000): Maximum word count to avoid massive files.
- **`min_text_ratio`** (0.1): Minimum ratio of text content to HTML markup.
- **`unified_score_threshold`** (40): The minimum quality score (0-100) required for indexing.
- **`consecutive_rejection_threshold`** (25): Stops crawling a domain if this many pages are rejected in a row.

### Filtering Lists

- **`EXCLUDED_TITLE_PATTERNS`**: Regex patterns for non-content titles (e.g., "Privacy Policy", "Login").
- **`EXCLUDED_URL_PATTERNS`**: Regex for structural URLs to avoid (e.g., `/tag/`, `/search/`).
- **`BINARY_EXTENSIONS`**: File extensions to skip (images, videos, executables).

### Detection Dictionaries

- **`CTA_PHRASES`**: Marketing language (e.g., "Book a Demo").
- **`MARKETING_TOOLS`**: Tech stack signatures (e.g., HubSpot, Marketo).
- **`AD_NETWORKS`**: Domains associated with ad serving (e.g., DoubleClick).
- **`TRACKING_SCRIPTS`**: Analytics and tracking patterns.
- **`PERSONAL_DOMAIN_KEYWORDS`**: Positive signals for personal blogs.

## Core Logic Functions

`config.py` implements the following quality assessment algorithms via `evaluate_page_quality()`:

### Rejection Reasons

When a page fails quality checks, the system returns one or more of the following standardized rejection reasons:

| Reason | Description |
|--------|-------------|
| `Corporate page` | Page detected as corporate/commercial. Two thresholds apply:<br>- **Immediate rejection**: Corporate score > 80 (hard corporate/e-commerce)<br>- **Standard rejection**: Corporate score >= 10 (in final quality check) |
| `ML classified as low quality` | ML model flagged content as low quality (simplified message) |
| `Unified quality score too low (X)` | Combined heuristic score below threshold (default: 40) |
| `Text-to-HTML ratio too low (X)` | Content density below minimum threshold (default: 0.1) |
| `Readability score out of range (X)` | Flesch Reading Ease outside acceptable bounds (20-100) |

Note: Corporate-related rejections are consolidated under a single "Corporate page" reason.

### `calculate_text_ratio(html_content)`

Calculates the density of meaningful text relative to HTML markup.

- **Features**:
  - Strips non-content tags (scripts, styles, navs).
  - Penalizes high link density (navigation menus).
  - Checks explicitly for natural language using stopword density.

### `calculate_ad_score(html)`

Quantifies the presence of advertising and tracking technology (0-100).

- **Factors**:
  - Presence of known ad network domains.
  - Tracking script signatures.
  - Density of ad-specific HTML elements/classes.
  - Excessive iframe usage.

### `calculate_corporate_score(url, html, text)`

Detects commercial intent, e-commerce, and low-quality content mills (0-100).

- **Signals**:
  - **Commercial Paths**: `/pricing`, `/product`.
  - **E-commerce**: Detected via `is_ecommerce_page` (cart, checkout buttons).
  - **Content Mills**: "Trending now", "Viral", "Source:".
  - **Sales Copy**: "Trusted by", "Maximize your...".
  - **CTAs**: High density of "Sign Up" or "Buy" buttons.

### `calculate_unified_score(scores)`

Synthesizes individual metrics into a final decision score.

- **Inputs**: Text ratio, Readability, Ad Score, Corporate Score.
- **Logic**:
  - Rewards high content density.
  - Penalizes high corporate/commercial scores.
  - Penalizes high ad density.

## Usage

Import `config` to access settings or functions:

```python
from provoke.config import config, calculate_unified_score

# Access a setting
db_path = config.DATABASE_PATH

# Use a logic function
score = calculate_unified_score(my_score_dict)
```
