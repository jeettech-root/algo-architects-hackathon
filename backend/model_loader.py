import os
import re
import math
import joblib
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse
from collections import Counter

import tldextract

TLD_EXTRACTOR = tldextract.TLDExtract(
    cache_dir=None,
    suffix_list_urls=(),
    fallback_to_snapshot=True,
)

MODEL_PATH_ENV = "MODEL_PATH"

FEATURE_NAMES = [
    "url_length",
    "num_dots",
    "has_https",
    "has_ip",
    "num_hyphens",
    "num_slashes",
    "subdomain_count",
    "domain_length",
    "entropy",
    "digit_ratio",
    "path_length",
    "query_length",
    "suspicious_tld",
    "fake_subdomain",
    "brand_mismatch",
    "is_trusted_domain",
]


def has_ip(url: str) -> int:
    return 1 if re.search(r"\d+\.\d+\.\d+\.\d+", url) else 0


def url_entropy(url: str) -> float:
    prob = [n / len(url) for n in Counter(url).values()]
    return -sum(p * math.log2(p) for p in prob)


def digit_ratio(url: str) -> float:
    digits = sum(c.isdigit() for c in url)
    return digits / len(url) if len(url) > 0 else 0.0


def get_tld(url: str) -> str:
    ext = TLD_EXTRACTOR(url)
    return ext.suffix


def has_suspicious_tld(url: str) -> int:
    bad_tlds = ["xyz", "ru", "tk", "ml", "ga", "cf"]
    return 1 if get_tld(url) in bad_tlds else 0


def is_fake_subdomain(url: str) -> int:
    ext = TLD_EXTRACTOR(url)
    subdomain = ext.subdomain
    brands = ["google", "amazon", "facebook", "paypal", "bank"]
    return 1 if any(b in subdomain for b in brands) else 0


def brand_mismatch(url: str) -> int:
    ext = TLD_EXTRACTOR(url)
    domain = ext.domain
    brands = ["google", "amazon", "facebook", "paypal"]
    return 1 if any(b in url and b != domain for b in brands) else 0


def is_trusted_domain(url: str) -> int:
    ext = TLD_EXTRACTOR(url)
    domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
    trusted_domains = [
        "google.com",
        "amazon.com",
        "amazon.in",
        "github.com",
        "microsoft.com",
        "facebook.com",
        "apple.com",
        "twitter.com",
        "linkedin.com",
        "instagram.com",
        "youtube.com",
        "wikipedia.org",
        "reddit.com",
        "netflix.com",
        "paypal.com",
    ]
    return 1 if domain in trusted_domains else 0


def extract_features(url: str) -> List[float]:
    parsed = urlparse(url)
    features = [
        float(len(url)),
        float(url.count(".")),
        1.0 if parsed.scheme == "https" else 0.0,
        float(has_ip(url)),
        float(url.count("-")),
        float(url.count("/")),
        float(len(parsed.netloc.split(".")) - 2 if parsed.netloc else 0),
        float(len(parsed.netloc)),
        float(url_entropy(url)),
        float(digit_ratio(url)),
        float(len(parsed.path)),
        float(len(parsed.query)),
        float(has_suspicious_tld(url)),
        float(is_fake_subdomain(url)),
        float(brand_mismatch(url)),
        float(is_trusted_domain(url)),
    ]
    return features


class LocalModel:
    def __init__(self, model_path: str = "model.pkl"):
        self.model_path = self.resolve_model_path(model_path)
        env_path = (
            self.resolve_model_path(os.getenv(MODEL_PATH_ENV, ""))
            if os.getenv(MODEL_PATH_ENV)
            else None
        )
        self.model = self.load_model(env_path or self.model_path)

    def resolve_model_path(self, model_path: str) -> Path:
        path = Path(model_path)
        if path.is_absolute():
            return path

        cwd_path = Path.cwd() / path
        if cwd_path.exists():
            return cwd_path

        return Path(__file__).resolve().parent / path

    def load_model(self, path: Path) -> object:
        if not path.exists():
            raise FileNotFoundError(f"Local model not found at {path}")
        model = joblib.load(path)
        if not hasattr(model, "predict"):
            raise ValueError("Loaded model does not implement predict()")
        return model

    def predict(self, url: str) -> Tuple[int, float]:
        features = extract_features(url)
        prediction = int(self.model.predict([features])[0])

        probability = 1.0
        if hasattr(self.model, "predict_proba"):
            proba_array = self.model.predict_proba([features])
            if len(proba_array) and len(proba_array[0]):
                probability = float(max(proba_array[0]))

        return prediction, probability
