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
source venv/bin/activate
python -c "
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

Create a script to test different parameters:

```python
# hyperparameter_tuning.py
from ml_train import train_fasttext_model, evaluate_model

configs = [
    {'lr': 0.5, 'epoch': 25, 'wordNgrams': 2, 'dim': 100},  # Current
    {'lr': 0.3, 'epoch': 50, 'wordNgrams': 3, 'dim': 150},  # More epochs, larger
    {'lr': 0.7, 'epoch': 30, 'wordNgrams': 2, 'dim': 100},  # Higher learning rate
    {'lr': 0.5, 'epoch': 25, 'wordNgrams': 3, 'dim': 100},  # Trigrams
]

for i, config in enumerate(configs):
    print(f"\n=== Config {i+1} ===")
    print(config)
    train_fasttext_model('data/train.txt', f'models/test_{i}.bin', **config)
    evaluate_model(f'models/test_{i}.bin', 'data/test.txt')
```

**Key parameters to adjust:**

- `epoch`: More epochs = more training (try 30-50)
- `wordNgrams`: Capture phrases (try 2-3)
- `dim`: Vector dimensions (try 100-200)
- `lr`: Learning rate (try 0.3-0.7)

---

### 3. **Adjust Classification Threshold**

Instead of accepting the top prediction, use confidence thresholds:

```python
# In quality_filter.py or wherever you use the model
def classify_with_threshold(model, text, threshold=0.7):
    labels, confidences = model.predict(text)

    if confidences[0] < threshold:
        # Low confidence - mark as "unsure" or apply stricter rules
        return "unsure"

    return labels[0].replace("__label__", "")
```

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

Combine multiple signals:

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

```python
# Find low-confidence predictions
def find_uncertain_predictions(model, unlabeled_data):
    uncertain = []

    for item in unlabeled_data:
        labels, confidences = model.predict(item['text'])

        # Low confidence = uncertain
        if confidences[0] < 0.7:
            uncertain.append({
                'url': item['url'],
                'confidence': confidences[0],
                'prediction': labels[0]
            })

    return sorted(uncertain, key=lambda x: x['confidence'])
```

**Workflow:**

1. Run model on unlabeled data
2. Export low-confidence predictions
3. Manually label these
4. Retrain model
5. Repeat

---

### 7. **Specific Fixes for Your Errors**

#### For False Positives (Bad→Good):

Most are **homepages** or **index pages**. Add rules:

```python
# In quality_filter.py
def is_likely_homepage(url, title, content):
    # Short content
    if len(content) < 800:
        # Generic titles
        if any(word in title.lower() for word in ['home', 'welcome', 'index']):
            return True

        # Root URL
        if url.endswith('/') or url.count('/') <= 3:
            return True

    return False
```

#### For False Negatives (Good→Bad):

Most are **RSS feeds** or **minimal pages**. Add exceptions:

```python
def is_special_format(url, title):
    # RSS/Atom feeds
    if url.endswith('.xml') or '/feed' in url or '/rss' in url:
        return True

    # Known good minimal pages
    if 'say hi' in title.lower() or 'contact' in title.lower():
        return True

    return False
```

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

Track these metrics over time:

```python
# Add to ml_train.py
def detailed_metrics(model, test_file):
    # ... existing code ...

    print(f"\nError Rate by Confidence:")
    print(f"High confidence (>0.9) errors: {high_conf_errors}")
    print(f"Medium confidence (0.7-0.9) errors: {med_conf_errors}")
    print(f"Low confidence (<0.7) errors: {low_conf_errors}")
```

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
