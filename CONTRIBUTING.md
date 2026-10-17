# Contributing to Hager Witty Solar Wallbox

Thank you for your interest in contributing to this project! Here are a few guidelines to help you get started.

## How to Contribute

### Reporting Bugs & Feature Requests
* Search existing issues before creating a new one to avoid duplicates.
* Use the provided issue templates and describe your problem or suggestion as clearly as possible.

### Submitting Pull Requests (PR)
1. Fork the repository and create your branch from `main`.
2. Ensure your code follows the official Home Assistant development guidelines.
3. Make sure all automated GitHub Actions tests pass before requesting a review:
   * **Hassfest validation:** Checks the integration's file structure and manifest.
   * **HACS validation:** Verifies compatibility with the Home Assistant Community Store.
   * **Pytest:** Runs the translation/consistency and coordinator-logic tests in `tests/` (Python 3.14, `pip install pytest pytest-homeassistant-custom-component pymodbus`).
4. Open the Pull Request with a clear description of the changes.

### Reporting issues with a real wallbox
Many features depend on the wallbox firmware (see the README). Please include the **firmware version** shown on the device page and, if possible, the diagnostics download and a debug log.

Thank you for making this integration better!
