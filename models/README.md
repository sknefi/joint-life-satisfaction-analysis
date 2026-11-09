# Versioned model artifact

`evs_v0_1_0.joblib` is the frozen v0.1.0 prediction bundle, including fitted
preprocessing, class ordering, supported countries and the selected estimator.
Its companion metadata records the file checksum, software versions, training
size, selection rule and prediction scope.

Use the exact recorded modelling dependency versions from `requirements-lock.txt`
for the released artifact. `evs-predict` defaults to this relative file path when
run from the repository root; elsewhere supply `--model /absolute/path/to/file`.
The wheel installs code; keep the model file and its metadata alongside it.

The model is trained on the training partition only. The production validation
partition checks the frozen choice; it is not added to training. The same-country
and six-country final prediction tests are reserved for Assure.

Only load the project's trusted artifact. Joblib files contain executable Python
serialization and are not a safe interchange format for arbitrary uploads.
