# Contributing to Hager Witty Modbus

Thank you for your interest in contributing to this project! Here are a few guidelines to help you get started.

## How to Contribute

### Reporting Bugs & Feature Requests
* Search existing issues before creating a new one to avoid duplicates.
* Use the provided issue templates and describe your problem or suggestion as clearly as possible.
* For register problems please attach the **debug log** (`custom_components.hager_witty: debug`) and your wallbox firmware version.

### Submitting Pull Requests (PR)
1. Fork the repository and create your branch from `main`.
2. Ensure your code follows the official Home Assistant development guidelines.
3. Make sure all automated GitHub Actions pass before requesting a review:
   * **Hassfest validation:** Checks the integration's file structure and manifest.
   * **HACS validation:** Verifies compatibility with the Home Assistant Community Store.
   * **Tests:** `pip install -r requirements_test.txt && pytest tests`
4. Open the Pull Request with a clear description of the changes.

### Where things live
* `registers.py` – the complete register map of the WittyPlus Modbus guide (pure Python, no Home Assistant imports).
  Adding a register means: add it to `REGISTERS`, make sure it lies in a block of `POLL_BLOCKS`, add entity + translations.
* `translations/en.json` is the source; `strings.json` must stay identical to it. New languages: copy `en.json`, translate only the values.

Thank you for making this integration better!
