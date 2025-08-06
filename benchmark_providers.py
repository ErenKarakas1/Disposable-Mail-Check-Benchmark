import argparse
from enum import Enum
import requests
import time
import os
import pandas as pd
from typing import List, Dict, Any, Callable, Union
from dotenv import load_dotenv

load_dotenv()

Provider = Dict[str, Any]
Result = Dict[str, Union[bool, float]]

class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"

# ------------------------
# EDIT THIS SECTION
# ------------------------
PROVIDERS: List[Provider] = [
    {
        "name": "Bouncer",
        "endpoint": "https://api.usebouncer.com/v1.1/email/verify",
        "method": HttpMethod.GET,
        "headers": {
            "x-api-key": os.getenv("BOUNCER_API_KEY")
        },
        "params": {
            "email": None
        },
        "map_func": lambda resp: resp.get("domain", {}).get("disposable") == "yes" # type: ignore
    },
    {
        "name": "Emailable",
        "endpoint": "https://api.emailable.com/v1/verify",
        "method": HttpMethod.GET,
        "headers": {},
        "params": {
            "email": None,
            "api_key": os.getenv("EMAILABLE_API_KEY")
        },
        "map_func": lambda resp: resp.get("disposable", False) # type: ignore
    },
    {
        "name": "Bouncify",
        "endpoint": "https://api.bouncify.io/v1/verify",
        "method": HttpMethod.GET,
        "headers": {
            "Accept": "*/*",
            "Content-Type": "application/json"
        },
        "params": {
            "apikey": os.getenv("BOUNCIFY_API_KEY"),
            "email": None
        },
        "map_func": lambda resp: resp.get("disposable", 0) == 1 # type: ignore
    },
    {
        "name": "Mail-Check",
        "endpoint": "https://mailcheck.p.rapidapi.com",
        "method": HttpMethod.GET,
        "headers": {
            "x-rapidapi-host": "mailcheck.p.rapidapi.com",
            "x-rapidapi-key": os.getenv("MAILCHECK_API_KEY"),
        },
        "params": {
            "domain": "mailinator.com"
        },
        "map_func": lambda resp: resp.get("disposable", False) # type: ignore
    },
    {
        "name": "Reoon",
        "endpoint": "https://emailverifier.reoon.com/api/v1/verify",
        "method": HttpMethod.GET,
        "headers": {},
        "params": {
            "email": None,
            "key": os.getenv("REOON_API_KEY"),
            "mode": "quick"
        },
        "map_func": lambda resp: resp.get("is_disposable", False) # type: ignore
    },
    {
        "name": "Debounce",
        "endpoint": "https://disposable.debounce.io",
        "method": HttpMethod.GET,
        "headers": {},
        "params": {
            "email": None,
        },
        "map_func": lambda resp: resp.get("disposable", "false").lower() == "true"  # type: ignore
    },
    {
        "name": "Kickbox",
        "endpoint": "https://api.kickbox.com/v2/verify",
        "method": HttpMethod.GET,
        "headers": {},
        "params": {
            "email": None,
            "apikey": os.getenv("KICKBOX_API_KEY")
        },
        "map_func": lambda resp: resp.get("disposable", False)  # type: ignore
    },
]
# ------------------------


def load_emails(path: str) -> List[str]:
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def test_provider(
    provider: Provider, email_list: List[str], expected_flag: bool
) -> List[Result]:
    results: List[Result] = []
    for email in email_list:
        params: Dict[str, Any] = {}
        for k, v in provider.get("params", {}).items():
            if v is None:
                params[k] = email
            else:
                params[k] = v
        
        url: str = provider["endpoint"]
        method: str = provider.get("method", HttpMethod.GET).value.upper()

        start = time.time()
        try:
            if method == "GET":
                resp = requests.get(
                    url, headers=provider.get("headers", {}), params=params, timeout=10
                )
            else:
                resp = requests.request(
                    method,
                    url,
                    headers=provider.get("headers", {}),
                    params=params,
                    timeout=10,
                )
            elapsed = (time.time() - start) * 1000
            data = resp.json()
            map_func: Callable[[str], bool] = provider["map_func"]
            print(data) # For debugging purposes, remove if you desire
            predicted_flag = bool(map_func(data))
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            predicted_flag = False
            print(f"Error testing {provider.get('name')} on {email}: {e}")

        results.append({"predicted": predicted_flag, "expected": expected_flag, "time_ms": elapsed})

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark disposable email verification providers")
    parser.add_argument("--missed", required=True, help="File of disposable emails missed by $PROVIDER")
    parser.add_argument("--detected", help="File of disposable emails identified by $PROVIDER")
    parser.add_argument("--normal", required=True, help="File of normal (non-disposable) emails")
    args = parser.parse_args()

    missed = load_emails(args.missed)
    detected = load_emails(args.detected) if args.detected else []
    normal = load_emails(args.normal)
    disposable_emails = missed + detected

    summary_records: List[Dict[str, Union[str, int, float]]] = []
    for provider in PROVIDERS:
        results_disposable = test_provider(provider, disposable_emails, True)
        results_normal = test_provider(provider, normal, False)
        all_results = results_disposable + results_normal

        true_positives: int = sum(1 for r in all_results if r["predicted"] and r["expected"])
        false_negatives = sum(1 for r in all_results if not r["predicted"] and r["expected"])
        false_positives = sum(1 for r in all_results if r["predicted"] and not r["expected"])
        true_negatives = sum(1 for r in all_results if not r["predicted"] and not r["expected"])

        total_requests = len(all_results)
        avg_response_time = (
            sum(r["time_ms"] for r in all_results) / total_requests
            if total_requests else 0
        )

        accuracy = (
            (true_positives + true_negatives) / total_requests 
            if total_requests else 0
        )
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) else 0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) else 0
        )

        summary_records.append(
            {
                "Provider": provider["name"],
                "Total Requests": total_requests,
                "Average Response (ms)": round(avg_response_time, 2),
                "True Positives": true_positives,
                "False Negatives": false_negatives,
                "False Positives": false_positives,
                "True Negatives": true_negatives,
                "Accuracy": round(accuracy, 3),
                "Precision": round(precision, 3),
                "Recall": round(recall, 3),
            }
        )

    df = pd.DataFrame(summary_records)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
