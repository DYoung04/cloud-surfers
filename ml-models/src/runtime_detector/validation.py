import argparse
from pathlib import Path
from .paths import PROJECT_ROOT
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Validate a dataset without changing it")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data/raw/training/invocations.csv")
    df = pd.read_csv(parser.parse_args().input)
    
    features = [
        "duration_ms",
        "invocation_count",
        "api_call_count",
        "access_denied_count",
        "error_count",
        "unexpected_target",
        "suspicious_input",
        "sensitive_api_call_count"
    ]
    
    print("Records:", len(df))
    print("Missing values:", df.isnull().sum().sum())
    print("Duplicate request IDs:", df["request_id"].duplicated().sum())
    print("Negative values:", (df[features] < 0).sum().sum())
    print("Labels:")
    print(df["label"].value_counts())
    # print(df.isnull().sum())


if __name__ == "__main__":
    main()
