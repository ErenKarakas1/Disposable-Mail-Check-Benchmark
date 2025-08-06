This script measures accuracy and response times of multiple email verification APIs.

### Usage

```bash
python benchmark_email_providers.py \
    --missed missed.txt \
    [--detected detected.txt] \
    --normal normal.txt
```

### Configuration
1. Edit the PROVIDERS list in the code. For each provider, specify:
    - name: unique provider name
    - endpoint
    - method: GET or POST
    - headers
    - params: dict of query params, use None as placeholder for the email field
    - map_func: a function that takes the parsed JSON response and returns True if the email is disposable, False otherwise

2. Supply your email lists as newline-separated text files.
    - missed.txt: disposable emails missed by $PROVIDER
    - detected.txt: disposable emails identified by $PROVIDER
    - normal.txt: normal (non-disposable) emails

### Output
A summary table printed to console with per-provider metrics with columns:
    
total requests, avg response time (ms), true positives, false negatives, false positives, true negatives, accuracy, precision, recall
