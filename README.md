# FinOpsSentinel 🛡️
> **An Autonomous AI-Powered Cloud Cost & Orphan Resource Agent**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Azure](https://img.shields.io/badge/Azure-SDK-0078D4.svg)
![AI Framework](https://img.shields.io/badge/AI-Groq%20%2F%20Llama%203-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**FinOpsSentinel** is an intelligent, autonomous agent designed to detect, analyze, and safely clean up orphaned cloud infrastructure on Microsoft Azure. By combining cloud telemetry APIs with modern LLM reasoning and function calling, FinOpsSentinel eliminates cloud waste, reduces unattached storage costs, and generates actionable cost optimization reports.

---

## 🌟 Key Features

- 🔍 **Automated Resource Scanning:** Periodically scans Azure subscriptions to discover orphaned assets (e.g., unattached managed disks, unassigned public IP addresses, and idle network interfaces).
- 🧠 **AI-Powered Risk Analysis:** Uses Llama 3 via Groq (or GPT-4o-mini) to evaluate logs, metadata, and tags before recommending deletion.
- 🛡️ **Built-in Safety Guardrails:** Defaults to `--dry-run` and audit mode to prevent accidental deletion of critical infrastructure.
- 🛠️ **Function Calling Integration:** Employs structured tool calling to trigger quarantine, tagging, or deletion tasks safely.
- ⏱️ **Scheduled Execution:** Runs on an automated schedule via Linux `cron` jobs or GitHub Actions workflows.

---

## 🏗️ Architecture Overview

┌──────────────────────┐      ┌──────────────────────────┐

│  Azure Subscription  │ ───► │  Azure Python SDK        │

│  (Disks, IPs, NICs)  │      │  (Resource Discovery)    │

└──────────────────────┘      └────────────┬─────────────┘

│ Raw Metadata

▼

┌──────────────────────┐      ┌──────────────────────────┐

│   FinOpsSentinel     │ ◄─── │  LLM Inference Engine    │

│   Action Executor    │ ───► │  (Groq / Llama 3)        │

└──────────┬───────────┘      └──────────────────────────┘

│

├─► 📄 Markdown Cost & Audit Reports

└─► 🏷️ Resource Tagging / Safe Quarantine


## 🧰 Tech Stack & Tools

- **Language:** Python 3.11+
- **Cloud Platform:** Microsoft Azure (`azure-identity`, `azure-mgmt-compute`, `azure-mgmt-network`)
- **AI / LLM:** Groq API / OpenAI API (Llama 3 / GPT-4o-mini)
- **Environment:** Linux (Ubuntu via GitHub Codespaces)
- **CI/CD & Automation:** GitHub Actions / Bash Cron

---

## 🚀 Quickstart Guide

### Prerequisites

1. An **Azure Subscription** (e.g., Azure for Students).
2. A free **Groq API Key** or **OpenAI API Key**.
3. **Python 3.11+** installed (or launch directly in **GitHub Codespaces**).

---

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone [https://github.com/YOUR-USERNAME/FinOpsSentinel.git](https://github.com/YOUR-USERNAME/FinOpsSentinel.git)
cd FinOpsSentinel

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```
### 2. Environment Variables

AZURE_SUBSCRIPTION_ID="your-azure-subscription-id"
GROQ_API_KEY="your-groq-api-key"
### 3. Authentication & Execution
Authenticate with your Azure account via Azure CLI:

```bash
az login
```
Run the FinOpsSentinel scanner in dry-run mode:

```bash
python main.py --mode audit --dry-run
```
## 📊 Sample Report Output
```JSON
{
  "timestamp": "2026-07-21T12:00:00Z",
  "scanned_resources": 14,
  "orphaned_count": 2,
  "estimated_monthly_waste_usd": 42.00,
  "findings": [
    {
      "resource_id": "/subscriptions/.../disks/dev-test-disk-01",
      "type": "Unattached Managed Disk",
      "size_gb": 128,
      "ai_risk_assessment": "LOW",
      "ai_reasoning": "Disk has been unattached for 45 days and contains no production tags.",
      "recommended_action": "TAG_FOR_DELETION"
    }
  ]
}
```
## 🛣️ Roadmap
[x] v1.0: Core Azure Scanner for Unattached Disks & Unused Public IPs

[ ] v1.5: LLM Function Calling for automatic resource tagging

[ ] v2.0: Multi-Cloud extension (AWS EBS & GCP Persistent Disk support)
DRY_RUN=True
## 📄 License

Distributed under the MIT License. See LICENSE for details.
