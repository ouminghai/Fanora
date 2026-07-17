"""Prometheus metrics for HTTP, Agent, and external model calls."""

from prometheus_client import Counter, Histogram

http_requests_total = Counter(
    "fanora_http_requests_total",
    "Total Fanora HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "fanora_http_request_duration_seconds",
    "Fanora HTTP request duration",
    ["method", "endpoint"],
)
fan_profile_runs_total = Counter(
    "fanora_profile_runs_total",
    "Fan profile analysis runs",
    ["source", "status"],
)
llm_inference_duration_seconds = Histogram(
    "fanora_llm_inference_duration_seconds",
    "LLM inference duration",
    ["model"],
)
