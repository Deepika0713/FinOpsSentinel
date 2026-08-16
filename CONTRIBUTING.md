# Contributing to FinOpsSentinel 🛡️
Thank you for your interest in contributing to FinOpsSentinel! To maintain code quality, security, and architectural consistency across the repository, please follow these guidelines when submitting pull requests or writing code.

---

## 🏗️ Repository Architecture & Import Standards
All core application logic lives within the myModule/ package directory.
- Package Structure: Ensure all Python modules (```azure_scanner.py```, ```ai_auditor.py```, ```remediator.py```, ```reporter.py```, ```guardrails.py```, ```tools.py```) remain inside ```myModule/```.
- Package Initialization: Never remove or rename ```myModule/__init__.py```.
- Import Style: All imports inside ```FinOpsSentinel.py``` or other top-level scripts must use package-level imports:
```python
# ✅ CORRECT
from myModule.azure_scanner import scan_resources
from myModule.remediator import apply_cleanup

# ❌ INCORRECT
import azure_scanner
```
---

## 🎨 Code Style & Standards
- **PEP 8 Alignment:** Follow standard Python PEP 8 formatting (4-space indentation, snake_case function/variable names, PascalCase class names).
- **CLI-First Philosophy:** Keep modules lightweight. Avoid adding heavy web or GUI dependencies unless specified in the roadmap.
- **Safety First (HITL Checks):** Any module that modifies or deletes Azure infrastructure must route execution through `myModule/guardrails.py` to require explicit user confirmation (`YES`).
- State Accuracy: If your feature deletes or alters cloud resources, you must invoke a re-scan before calling `myModule/reporter.py` to ensure final reports (`report_latest.md` and `finops_audit_report.json`) reflect real-time cloud state.

---
## ⚡ Local Development Workflow

Look at the `README.md` to bring the repo to your local machine...

---
## 🔄 Commit & Pull Request Guidelines
1. **Create a Feature Branch:**
```bash
git checkout -b feature/add-new-scanner
```
2. **Keep Commits Concise:** Write descriptive commit messages (e.g., `feat(scanner): add unattached NSG detection`).
3. **Update Documentation:** If you add a new scanner or change environment variables, update `README.md` and `.env.example` accordingly.
4. **Submit Pull Request:** Open a PR against the main branch. Ensure all automated GitHub Actions Docker builds pass.

---
Thank you for helping build a safer, more efficient FinOps tool!
