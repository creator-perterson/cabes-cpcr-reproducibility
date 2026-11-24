# Environment

The bounded checks in this repository use Python 3.10 or newer and the standard library. No historical runtime version is asserted because the R3.1 records do not provide a complete execution identity for every dependency.

The historical runtime is not included and its complete version identity remains unverified. Model weights, tokenizers, datasets, and private Reader artifacts are excluded.

The GitHub workflow installs the `tokenizers`, NumPy and SciPy dependencies for synthetic CLI tests and full offline R14 statistics. It does not download model weights or start formal experiments. Install the same requirement files for local validation.

Full R14 statistical replay used NumPy 2.2.6 and SciPy 1.15.3 in the available Python 3.10 runtime. Plot regeneration used local Anaconda Python and Matplotlib 3.11.0. These are observed prior environments, not a complete historical runtime attestation. `statistics-requirements.txt` and `plotting-requirements.txt` record separate dependencies.
