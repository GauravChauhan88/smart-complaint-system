import os
import re
import json
import torch
import torch.nn as nn
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from transformers import AutoTokenizer, AutoModel

# ----------------- Database Setup -----------------
DATABASE_URL = "sqlite:///./complaints.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ComplaintDB(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), default="Anonymous")
    customer_email = Column(String(100), default="customer@example.com")
    text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    category_confidence = Column(Float, nullable=False)
    urgency = Column(String(20), nullable=False)
    urgency_confidence = Column(Float, nullable=False)
    extracted_entities = Column(Text, default="{}")
    status = Column(String(20), default="Open")
    assigned_agent = Column(String(100), default="Unassigned")
    needs_manual_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- Model Architecture & Inference -----------------
MODEL_DIR = "ml-pipeline/saved_model"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

with open(f"{MODEL_DIR}/label_mappings.json", "r") as f:
    mappings = json.load(f)

id2cat = {int(v): k for k, v in mappings["category_to_id"].items()}
id2urg = {int(v): k for k, v in mappings["urgency_to_id"].items()}

class MultiTaskDistilBERT(nn.Module):
    def __init__(self, num_categories, num_urgencies):
        super(MultiTaskDistilBERT, self).__init__()
        self.bert = AutoModel.from_pretrained("distilbert-base-uncased")
        self.dropout = nn.Dropout(0.3)
        self.category_classifier = nn.Linear(self.bert.config.hidden_size, num_categories)
        self.urgency_classifier = nn.Linear(self.bert.config.hidden_size, num_urgencies)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs[0][:, 0, :]
        pooled = self.dropout(pooled)
        return self.category_classifier(pooled), self.urgency_classifier(pooled)

print(f"Loading inference weights onto {device}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = MultiTaskDistilBERT(len(id2cat), len(id2urg)).to(device)
model.load_state_dict(torch.load(f"{MODEL_DIR}/model_weights.pt", map_location=device, weights_only=True))
model.eval()
print("Model loaded successfully.")

def run_hybrid_inference(text: str):
    # 1. Neural Transformer Forward Pass
    inputs = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=128,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        cat_logits, urg_logits = model(inputs["input_ids"], inputs["attention_mask"])
        cat_probs = torch.softmax(cat_logits, dim=1).squeeze(0)
        urg_probs = torch.softmax(urg_logits, dim=1).squeeze(0)

        cat_id = torch.argmax(cat_probs).item()
        urg_id = torch.argmax(urg_probs).item()

        cat_conf = round(float(cat_probs[cat_id].item()) * 100, 2)
        urg_conf = round(float(urg_probs[urg_id].item()) * 100, 2)
        predicted_category = id2cat[cat_id]
        predicted_urgency = id2urg[urg_id]

    # 2. Strict Entity Extraction (with word boundaries)
    entities = {}
    ref_match = re.search(r'\b(?:ref|ticket|order|txn|case)[\s#:]+([A-Za-z0-9\-]+)', text, re.IGNORECASE)
    if ref_match:
        val = ref_match.group(1).strip()
        if val.lower() not in ["erence", "er", "to", "the", "a"]:
            entities["reference_id"] = val

    amt_match = re.search(r'(?:[\$€₹]|Rs\.?\s*)(\d+(?:,\d+)*(?:\.\d+)?)', text)
    if amt_match:
        entities["amount"] = amt_match.group(0)

    # 3. Hybrid Urgency Guardrail with Word Boundary Matching
    critical_pattern = r'\b(fraud|unauthorized|attorney|lawyer|police|stolen|court|immediate|immediately)\b'
    high_pattern = r'\b(refund|missing|delivered|overdraft|penalty|chargeback|damaged)\b'
    low_pattern = r'\b(inquiry|clarification|update|policy|document|schedule|general|question|information)\b'

    if re.search(critical_pattern, text, re.IGNORECASE):
        predicted_urgency = "Critical"
        urg_conf = max(urg_conf, 98.5)
    elif re.search(high_pattern, text, re.IGNORECASE):
        if predicted_urgency in ["Low", "Medium"]:
            predicted_urgency = "High"
            urg_conf = max(urg_conf, 92.0)
    elif re.search(low_pattern, text, re.IGNORECASE) and not re.search(critical_pattern, text, re.IGNORECASE):
        predicted_urgency = "Low"
        urg_conf = max(urg_conf, 90.0)

    return {
        "category": predicted_category,
        "category_confidence": cat_conf,
        "urgency": predicted_urgency,
        "urgency_confidence": urg_conf,
        "extracted_entities": entities,
        "needs_manual_review": cat_conf < 65.0
    }

# ----------------- Seed Dataset -----------------
INITIAL_DEMO_COMPLAINTS = [
    {
        "customer_name": "Vikram Sethi",
        "customer_email": "vikram.sethi@gmail.com",
        "text": "URGENT FRAUD: An unauthorized international transaction of $1,240.00 was posted to my credit card without OTP confirmation. Block card and open case Ref#TXN-9901 immediately."
    },
    {
        "customer_name": "Ananya Roy",
        "customer_email": "ananya.roy@outlook.com",
        "text": "My package for Order#DLV-88210 was marked delivered by the courier 4 days ago but never reached my address. Need a refund or expedited re-shipment."
    },
    {
        "customer_name": "Rohan Malhotra",
        "customer_email": "rohan.m@techcorp.in",
        "text": "The web portal crashes with HTTP 500 error every time I attempt to export the annual tax invoice statement. Ticket Ref#TICK-3301. Please resolve."
    },
    {
        "customer_name": "Meera Nambiar",
        "customer_email": "meera.nambiar@yahoo.com",
        "text": "Hello, could your operations desk share the schedule for next quarter's interest calculation on recurring deposits? Thank you for the update."
    },
    {
        "customer_name": "Arjun Singhal",
        "customer_email": "arjun.s@singhalholdings.com",
        "text": "CRITICAL: Multiple duplicate charges totaling $450.00 debited from our business checking account on Ref#TXN-77402. Initiating legal dispute if not reverted."
    },
    {
        "customer_name": "Kavita Pillai",
        "customer_email": "kavita.p@gmail.com",
        "text": "Received a severely damaged item in Order#DLV-11029. The outer seal was broken and glass container inside was shattered in transit. Please issue replacement."
    },
    {
        "customer_name": "Siddharth Das",
        "customer_email": "siddharth.das@cloudnet.io",
        "text": "Our automated webhooks stopped receiving payload notifications after the recent v2 API maintenance release. Need urgent technical escalation Ref#DEV-504."
    },
    {
        "customer_name": "Pooja Hegde",
        "customer_email": "pooja.h@rediffmail.com",
        "text": "I was charged an overdraft penalty fee of $35.00 even though my salary transfer cleared on time. Please reverse this disputed fee Ref#FEE-9041."
    }
]

# ----------------- FastAPI Routes -----------------
app = FastAPI(title="Smart Customer Complaint System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def auto_seed_on_startup():
    db = SessionLocal()
    try:
        count = db.query(ComplaintDB).count()
        if count == 0:
            print("Database is empty. Populating with initial demo complaints...")
            for item in INITIAL_DEMO_COMPLAINTS:
                pred = run_hybrid_inference(item["text"])
                ticket = ComplaintDB(
                    customer_name=item["customer_name"],
                    customer_email=item["customer_email"],
                    text=item["text"],
                    category=pred["category"],
                    category_confidence=pred["category_confidence"],
                    urgency=pred["urgency"],
                    urgency_confidence=pred["urgency_confidence"],
                    extracted_entities=json.dumps(pred["extracted_entities"]),
                    needs_manual_review=pred["needs_manual_review"],
                    status="Open",
                    assigned_agent="Unassigned"
                )
                db.add(ticket)
            db.commit()
            print("Auto-seed complete: Initial complaints active.")
    finally:
        db.close()

class ComplaintCreate(BaseModel):
    customer_name: Optional[str] = "Customer"
    customer_email: Optional[str] = "customer@example.com"
    text: str

class ComplaintStatusUpdate(BaseModel):
    status: str
    assigned_agent: Optional[str] = None

@app.get("/api/health")
def health():
    return {"status": "online", "device": str(device)}

@app.post("/api/complaints")
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Complaint text cannot be empty.")

    pred = run_hybrid_inference(payload.text)

    complaint = ComplaintDB(
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        text=payload.text,
        category=pred["category"],
        category_confidence=pred["category_confidence"],
        urgency=pred["urgency"],
        urgency_confidence=pred["urgency_confidence"],
        extracted_entities=json.dumps(pred["extracted_entities"]),
        needs_manual_review=pred["needs_manual_review"],
        status="Open",
        assigned_agent="Unassigned"
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint

@app.get("/api/complaints")
def get_complaints(db: Session = Depends(get_db)):
    return db.query(ComplaintDB).order_by(ComplaintDB.id.desc()).all()

@app.patch("/api/complaints/{complaint_id}")
def update_complaint_status(complaint_id: int, payload: ComplaintStatusUpdate, db: Session = Depends(get_db)):
    complaint = db.query(ComplaintDB).filter(ComplaintDB.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    complaint.status = payload.status
    if payload.assigned_agent:
        complaint.assigned_agent = payload.assigned_agent
    db.commit()
    db.refresh(complaint)
    return complaint

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(ComplaintDB).count()
    critical = db.query(ComplaintDB).filter(ComplaintDB.urgency == "Critical").count()
    open_tickets = db.query(ComplaintDB).filter(ComplaintDB.status == "Open").count()
    needs_review = db.query(ComplaintDB).filter(ComplaintDB.needs_manual_review == True).count()
    return {
        "total_tickets": total,
        "critical_tickets": critical,
        "open_tickets": open_tickets,
        "needs_manual_review": needs_review
    }