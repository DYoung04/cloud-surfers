from pathlib import Path
from .paths import PROJECT_ROOT
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def main():
    output = PROJECT_ROOT / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ("X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv")):
        raise FileExistsError("Existing Phase 4 split preserved; archive it explicitly before regenerating")
    df = pd.read_csv(PROJECT_ROOT / "data/raw/training/invocations.csv")
    
    print(df.head())
    print(df.info())
    print(df["label"].value_counts())
    # print(df.isnull().sum())
    print("Duplicate rows:", df.duplicated().sum())
    
    feature_cols = [
        "duration_ms",
        "invocation_count",
        "api_call_count",
        "access_denied_count",
        "error_count",
        "unexpected_target",
        "suspicious_input",
    ]
    
    X = df[feature_cols]
    y = df["label"]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )
    
    print("Training:", len(X_train))
    print("Testing:", len(X_test))
    
    print(y_train.value_counts())
    print(y_test.value_counts())
    
    scaler = StandardScaler()
    
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    X_train.to_csv(PROJECT_ROOT / "data/processed/X_train.csv", index=False)
    X_test.to_csv(PROJECT_ROOT / "data/processed/X_test.csv", index=False)
    
    y_train.to_csv(PROJECT_ROOT / "data/processed/y_train.csv", index=False)
    y_test.to_csv(PROJECT_ROOT / "data/processed/y_test.csv", index=False)


if __name__ == "__main__":
    main()
