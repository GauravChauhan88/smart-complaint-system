import os
import re
import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split

DATA_DIR = "ml-pipeline/data"
os.makedirs(DATA_DIR, exist_ok=True)

def derive_urgency(text: str) -> str:
    lower = text.lower()
    critical_triggers = ["fraud", "stolen", "unauthorized", "lawyer", "attorney", "court", "police", "scam", "illegal", "threat"]
    high_triggers = ["urgent", "charged", "fee", "dispute", "refund", "overdraft", "violation", "terrible", "immediately", "fail", "lost"]
    medium_triggers = ["delay", "waiting", "inquiry", "clarification", "update", "when", "wrong", "issue", "problem", "help"]

    if any(k in lower for k in critical_triggers):
        return "Critical"
    elif any(k in lower for k in high_triggers):
        return "High"
    elif any(k in lower for k in medium_triggers):
        return "Medium"
    return "Low"

def prepare_real_data():
    print("Loading CFPB / Customer Complaints dataset...")
    dataset = load_dataset("hblim/customer-complaints", split="train")
    df = pd.DataFrame(dataset)

    label_map = {
        0: "Billing & Accounts",
        1: "Delivery & Fulfillment",
        2: "Product & Technical"
    }

    df["category"] = df["label"].map(label_map)
    df["complaint_text"] = df["text"].astype(str).str.strip()
    df = df[df["complaint_text"].str.len() > 20].copy()
    df["urgency"] = df["complaint_text"].apply(derive_urgency)

    # Balance urgency classes by sampling evenly across available pools
    dfs = []
    min_count = 250
    for u in ["Low", "Medium", "High", "Critical"]:
        sub = df[df["urgency"] == u]
        if len(sub) < min_count:
            # Upsample minority classes to ensure representation
            sub = sub.sample(min_count, replace=True, random_state=42)
        else:
            sub = sub.sample(min_count, replace=False, random_state=42)
        dfs.append(sub)

    balanced_df = pd.concat(dfs).sample(frac=1.0, random_state=42).reset_index(drop=True)

    train_df, test_df = train_test_split(
        balanced_df, test_size=0.2, random_state=42, stratify=balanced_df["urgency"]
    )

    train_path = f"{DATA_DIR}/train.csv"
    test_path = f"{DATA_DIR}/test.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"\nSaved balanced dataset:")
    print(f" -> Train: {len(train_df)} rows")
    print(f" -> Test:  {len(test_df)} rows")
    print("\nUrgency distribution in Train:\n", train_df["urgency"].value_counts())
    print("\nCategory distribution in Train:\n", train_df["category"].value_counts())

if __name__ == "__main__":
    prepare_real_data()