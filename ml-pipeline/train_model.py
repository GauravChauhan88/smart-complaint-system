import os
import json
import torch
import torch.nn as nn
from torch.optim import AdamW
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from sklearn.metrics import classification_report
from sklearn.utils.class_weight import compute_class_weight

MODEL_SAVE_DIR = "ml-pipeline/saved_model"
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Executing training on: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

class ComplaintDataset(Dataset):
    def __init__(self, texts, categories, urgencies, tokenizer, max_len=128):
        self.texts = texts
        self.categories = categories
        self.urgencies = urgencies
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt"
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "category_label": torch.tensor(self.categories[idx], dtype=torch.long),
            "urgency_label": torch.tensor(self.urgencies[idx], dtype=torch.long)
        }

class MultiTaskDistilBERT(nn.Module):
    def __init__(self, num_categories, num_urgencies):
        super(MultiTaskDistilBERT, self).__init__()
        self.bert = AutoModel.from_pretrained("distilbert-base-uncased")
        self.dropout = nn.Dropout(0.3)
        self.category_classifier = nn.Linear(self.bert.config.hidden_size, num_categories)
        self.urgency_classifier = nn.Linear(self.bert.config.hidden_size, num_urgencies)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs[0][:, 0, :]
        pooled_output = self.dropout(pooled_output)
        cat_logits = self.category_classifier(pooled_output)
        urg_logits = self.urgency_classifier(pooled_output)
        return cat_logits, urg_logits

def run_training():
    train_df = pd.read_csv("ml-pipeline/data/train.csv")
    test_df = pd.read_csv("ml-pipeline/data/test.csv")

    categories = sorted(train_df["category"].dropna().unique().tolist())
    urgencies = ["Low", "Medium", "High", "Critical"]

    cat2id = {c: i for i, c in enumerate(categories)}
    urg2id = {u: i for i, u in enumerate(urgencies)}

    with open(f"{MODEL_SAVE_DIR}/label_mappings.json", "w") as f:
        json.dump({"category_to_id": cat2id, "urgency_to_id": urg2id}, f, indent=4)

    train_df["cat_label"] = train_df["category"].map(cat2id)
    train_df["urg_label"] = train_df["urgency"].map(urg2id)
    test_df["cat_label"] = test_df["category"].map(cat2id)
    test_df["urg_label"] = test_df["urgency"].map(urg2id)

    # Compute loss weights to prevent class bias
    cat_weights = compute_class_weight("balanced", classes=np.unique(train_df["cat_label"]), y=train_df["cat_label"].values)
    urg_weights = compute_class_weight("balanced", classes=np.unique(train_df["urg_label"]), y=train_df["urg_label"].values)

    cat_weight_tensor = torch.tensor(cat_weights, dtype=torch.float).to(device)
    urg_weight_tensor = torch.tensor(urg_weights, dtype=torch.float).to(device)

    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    tokenizer.save_pretrained(MODEL_SAVE_DIR)

    train_dataset = ComplaintDataset(train_df["complaint_text"].tolist(), train_df["cat_label"].tolist(), train_df["urg_label"].tolist(), tokenizer)
    test_dataset = ComplaintDataset(test_df["complaint_text"].tolist(), test_df["cat_label"].tolist(), test_df["urg_label"].tolist(), tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    model = MultiTaskDistilBERT(num_categories=len(categories), num_urgencies=len(urgencies)).to(device)
    optimizer = AdamW(model.parameters(), lr=2e-5)
    
    criterion_cat = nn.CrossEntropyLoss(weight=cat_weight_tensor)
    criterion_urg = nn.CrossEntropyLoss(weight=urg_weight_tensor)

    epochs = 4
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=int(total_steps * 0.1), num_training_steps=total_steps)

    print("\nStarting training loop on RTX 4060...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0

        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            cat_targets = batch["category_label"].to(device)
            urg_targets = batch["urgency_label"].to(device)

            cat_preds, urg_preds = model(input_ids, attention_mask)
            loss = criterion_cat(cat_preds, cat_targets) + criterion_urg(urg_preds, urg_targets)
            loss.backward()
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_train_loss = total_loss / len(train_loader)
        print(f"Epoch {epoch + 1}/{epochs} | Average Training Loss: {avg_train_loss:.4f}")

    # Evaluation
    model.eval()
    all_cat_preds, all_cat_targets = [], []
    all_urg_preds, all_urg_targets = [], []

    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            cat_preds, urg_preds = model(input_ids, attention_mask)
            all_cat_preds.extend(torch.argmax(cat_preds, dim=1).cpu().tolist())
            all_urg_preds.extend(torch.argmax(urg_preds, dim=1).cpu().tolist())
            all_cat_targets.extend(batch["category_label"].tolist())
            all_urg_targets.extend(batch["urgency_label"].tolist())

    print("\n--- Test Set Evaluation: Category Classification ---")
    print(classification_report(all_cat_targets, all_cat_preds, target_names=categories, zero_division=0))

    print("\n--- Test Set Evaluation: Urgency Level Detection ---")
    print(classification_report(all_urg_targets, all_urg_preds, target_names=urgencies, zero_division=0))

    torch.save(model.state_dict(), f"{MODEL_SAVE_DIR}/model_weights.pt")
    print(f"\nModel artifacts successfully saved to {MODEL_SAVE_DIR}/")

if __name__ == "__main__":
    run_training()