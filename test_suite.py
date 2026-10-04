import pytest
from fastapi.testclient import TestClient
from backend.main import app, run_hybrid_inference

client = TestClient(app)

# 1. Unit Tests: Hybrid Inference & Entity Extraction
def test_critical_fraud_escalation():
    sample = "Urgent: An unauthorized transaction of $750 occurred on my debit card Ref#TXN-998811."
    result = run_hybrid_inference(sample)
    
    assert result["urgency"] == "Critical"
    assert result["category"] == "Billing & Accounts"
    assert "reference_id" in result["extracted_entities"]
    assert result["extracted_entities"]["reference_id"] == "TXN-998811"
    assert result["extracted_entities"]["amount"] == "$750"

def test_delivery_high_escalation():
    sample = "Order#DLV-44321 was reported delivered but parcel was missing and never arrived. I want a refund."
    result = run_hybrid_inference(sample)
    
    assert result["urgency"] == "High"
    assert result["category"] == "Delivery & Fulfillment"
    assert result["extracted_entities"]["reference_id"] == "DLV-44321"

def test_low_inquiry_classification():
    sample = "Could someone please send the updated policy document regarding account maintenance terms?"
    result = run_hybrid_inference(sample)
    
    assert result["urgency"] == "Low"
    assert result["extracted_entities"] == {}

# 2. Integration Tests: API Endpoints
def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_complaint_lifecycle():
    # Create complaint
    payload = {
        "customer_name": "Test Customer",
        "customer_email": "test@demo.com",
        "text": "CRITICAL: Unauthorized card usage for $350 Ref#SEC-101."
    }
    post_res = client.post("/api/complaints", json=payload)
    assert post_res.status_code == 200
    data = post_res.json()
    complaint_id = data["id"]
    assert data["urgency"] == "Critical"
    assert data["status"] == "Open"

    # Fetch stats
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_tickets"] >= 1

    # Resolve complaint
    patch_res = client.patch(f"/api/complaints/{complaint_id}", json={"status": "Resolved"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Resolved"