import time
import requests
from concurrent.futures import ThreadPoolExecutor

TARGET_URL = "http://127.0.0.1:8000/api/complaints"

SAMPLE_PAYLOADS = [
    {"customer_name": "Perf Tester 1", "customer_email": "t1@test.com", "text": "CRITICAL: Stolen debit card used for $400 unauthorized charge Ref#ST-100."},
    {"customer_name": "Perf Tester 2", "customer_email": "t2@test.com", "text": "Package tracking says delivered but parcel Order#DLV-880 is missing."},
    {"customer_name": "Perf Tester 3", "customer_email": "t3@test.com", "text": "Web application crashes with error 500 when exporting statement Ref#BUG-22."},
    {"customer_name": "Perf Tester 4", "customer_email": "t4@test.com", "text": "Please provide an update on quarterly interest rates."}
]

def send_request(idx):
    payload = SAMPLE_PAYLOADS[idx % len(SAMPLE_PAYLOADS)]
    start = time.time()
    try:
        res = requests.post(TARGET_URL, json=payload, timeout=10)
        latency = (time.time() - start) * 1000
        return res.status_code == 200, latency
    except Exception as e:
        return False, (time.time() - start) * 1000

def run_stress_test(total_requests=40, concurrency=4):
    print(f"Executing Load Test: {total_requests} requests at concurrency={concurrency}...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(send_request, range(total_requests)))

    total_time = time.time() - start_time
    successes = [r for r in results if r[0]]
    latencies = [r[1] for r in results if r[0]]

    success_rate = (len(successes) / total_requests) * 100
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    rps = total_requests / total_time

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Total Requests Processed: {total_requests}")
    print(f"Success Rate:             {success_rate:.1f}%")
    print(f"Total Duration:           {total_time:.2f}s")
    print(f"Throughput (RPS):         {rps:.2f} req/sec")
    print(f"Average Latency:          {avg_latency:.2f} ms")
    print(f"95th Percentile Latency:  {p95_latency:.2f} ms")
    print("===================================================\n")

if __name__ == "__main__":
    run_stress_test(total_requests=40, concurrency=4)