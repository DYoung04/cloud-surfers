# Research workflow and provenance

1. Preserve input measurements and CloudWatch exports in `data/raw/`.
2. Extract transformed data into `data/interim/`; validate labels and request IDs.
3. Preserve the established stratified 800/200 split in `data/processed/`.
4. Train both models on identical records. Fit the scaler on training data only.
5. Keep model artifacts under one model-run directory with their feature schema,
   scaler, and metadata. Offline evaluation lives in `experiments/training/`.
6. Run the deployed models separately on labeled test scenarios. Store each run's
   generator CSV and CloudWatch export together; join records by request ID.
7. Evaluate multiclass accuracy and binary attack detection separately. Count
   detection errors and missing detections explicitly. Analyze cold starts
   separately from warm inference, total detector work, and full Lambda duration.
8. Record results in `experiments/`; place presentation tables/figures in `reports/`.

The baseline and Logistic Regression runs currently have preserved raw records and
provenance manifests. No live Decision Tree run has been fabricated. No new model
training or AWS execution was performed during reorganization. Existing offline
predictions remain the original Phase 5 results.

Existing metadata was reconstructed only where the files supply evidence.
Original training/execution commit IDs were not recorded and remain null/unknown.
For future runs record UTC times, deployed model and artifact hashes, code commit,
Lambda runtime/architecture/memory/timeout, traffic pacing, random seed, environment
configuration excluding secrets, and counters/errors. Keep run identifiers unique.

The two duration definitions and the different 60-second count observation points
are documented in `data_dictionary.md`; do not silently treat them as equivalent.
Perfect binary accuracy on generated scenarios does not establish generalization
to previously unseen attacks.

Structure references:
- https://cookiecutter-data-science.drivendata.org/
- https://cookiecutter-data-science.drivendata.org/opinions/
