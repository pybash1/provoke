# Reducing False Positives and False Negatives

## Current Error Analysis

**False Positives (22):** Bad pages classified as Good

- Average confidence: 0.825 (fairly confident in wrong predictions)
- Examples: LessWrong homepage, fast.ai homepage, Ruby on Rails doctrine page

**False Negatives (4):** Good pages classified as Bad

- Average confidence: 0.721 (less confident)
- Examples: Blog posts, RSS feeds, personal websites

## Strategies to Reduce Errors

### 1. **Improve Training Data Quality**

#### Add More Examples of Edge Cases

```bash
# Export more data focusing on borderline cases
python train_classifier.py --export --limit 1000
```

**Action items:**

- Label more examples similar to the misclassified ones
- Add more "homepage" examples (many FPs are homepages)
- Add more "RSS feed" examples (FN includes an RSS feed)
- Add more "navigation/index" pages

#### Balance Your Dataset

Check the distribution:

```bash
# Count labels in your training data
uv run python -c "
import csv
good = bad = 0
with open('data/to_label_done.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['quality'] == 'good': good += 1
        elif row['quality'] == 'bad': bad += 1
print(f'Good: {good}, Bad: {bad}, Ratio: {good/bad:.2f}')
"
```

**Target:** Aim for roughly 1:2 to 1:3 ratio (good:bad) since bad pages are more common.

---

### 2. **Tune Model Hyperparameters**

Create a script to test different parameters (see `ml_train.py` for variables):

**Key parameters to adjust:**

- `epoch`: More epochs = more training (try 30-50)
- `wordNgrams`: Capture phrases (try 2-3)
- `dim`: Vector dimensions (try 100-200)
- `lr`: Learning rate (try 0.3-0.7)

---

### 3. **Adjust Classification Threshold**

Instead of accepting the top prediction, use confidence thresholds in `config.py` (under `ML_CONFIG`):

**Strategy:**

- For **false positives** (bad→good): Increase threshold for "good" classification
- For **false negatives** (good→bad): Lower threshold for "good" classification
- Use different thresholds for each class

---

### 4. **Feature Engineering**

#### A. Add Domain-Based Features

```python
# Extract domain patterns
from urllib.parse import urlparse

def extract_domain_features(url):
    domain = urlparse(url).netloc
    features = []

    # Known good domains
    if any(d in domain for d in ['benkuhn.net', 'maggieappleton.com', 'notes.andymatuschak.org']):
        features.append('TRUSTED_DOMAIN')

    # Known bad patterns
    if any(d in domain for d in ['amazon.', 'ycombinator.com', 'enable-javascript']):
        features.append('COMMERCIAL_DOMAIN')

    return ' '.join(features)

# Add to training data
training_text = f"{domain_features} url={url} title={title} {content}"
```

#### B. Add Title-Based Features

```python
def extract_title_features(title):
    features = []

    # Bad indicators
    bad_patterns = ['privacy policy', 'terms of use', 'sign in', 'log in', 'cart', 'home -']
    if any(p in title.lower() for p in bad_patterns):
        features.append('BAD_TITLE')

    # Good indicators
    good_patterns = ['how to', 'guide', 'tutorial', 'notes', 'blog']
    if any(p in title.lower() for p in good_patterns):
        features.append('GOOD_TITLE')

    return ' '.join(features)
```

---

### 5. **Ensemble Methods**

Combine multiple signals (as done in `ml_classifier.py`'s `enhanced_check`):

```python
def ensemble_classify(url, title, content):
    # 1. ML model prediction
    ml_label, ml_conf = model.predict(f"url={url} title={title} {content}")

    # 2. Rule-based checks
    rule_score = 0

    # Homepage detection (often FP)
    if len(content) < 500 and any(word in title.lower() for word in ['home', 'welcome']):
        rule_score -= 0.3

    # Blog post indicators (often FN)
    if any(word in url for word in ['/blog/', '/post/', '/article/']):
        rule_score += 0.2

    # 3. Combine scores
    final_score = ml_conf[0] + rule_score

    if final_score > 0.6:
        return "good"
    else:
        return "bad"
```

---

### 6. **Active Learning**

Focus on uncertain predictions:

**Workflow:**

1. Run `check_model_stats.py` on unlabeled data in the index.
2. Export low-confidence predictions.
3. Manually label these.
4. Retrain model.
5. Repeat.

---

### 7. **Specific Fixes for Your Errors**

#### For False Positives (Bad→Good):

Most are **homepages** or **index pages**. Add rules to `calculate_corporate_score` in `config.py` or filters in `landing_page_filter.py`.

#### For False Negatives (Good→Bad):

Most are **RSS feeds** or **minimal pages**. Add exceptions for known good structures.

---

## Recommended Action Plan

### Phase 1: Quick Wins (Today)

1. ✅ Run error analysis (done!)
2. Add rule-based filters for obvious patterns
3. Adjust classification threshold to 0.75

### Phase 2: Data Improvement (This Week)

1. Export 500 more examples
2. Focus on labeling:
   - Homepage/index pages (mark as bad)
   - RSS feeds (mark as good if from good sources)
   - Blog posts with minimal content
3. Retrain model

### Phase 3: Advanced Tuning (Next Week)

1. Hyperparameter tuning
2. Feature engineering (domain + title features)
3. Implement ensemble method
4. Set up active learning pipeline

---

## Monitoring

Track these metrics over time using `check_model_stats.py`.

**Goal:**

- Reduce FP from 22 → <10
- Keep FN low (<5)
- Maintain F1 score >0.95

---

## Expected Results

With these improvements:

- **Short term** (rules + threshold): FP: 22→15, FN: 4→6
- **Medium term** (more data): FP: 15→8, FN: 6→3
- **Long term** (full pipeline): FP: 8→5, FN: 3→2

Remember: Some errors are inevitable. Focus on the most impactful ones!
