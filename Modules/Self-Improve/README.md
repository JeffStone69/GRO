# XForge Self-Improvement Module (SIM)

**A secure, production-grade autonomous code evolution engine powered by the Grok API (xAI).**

---

## Overview

The **XForge Self-Improvement Module** (`SIM.py`) is an advanced, self-contained Python application designed to elevate software quality through intelligent, iterative analysis and refinement. By integrating the Grok large language model via the official xAI API, SIM systematically examines Python scripts—whether provided directly, uploaded as files, sourced from GitHub repositories, or informed by historical error logs and user directives—then generates precise improvement recommendations and complete, production-ready revised code.

Recent enhancements include refined Gradio interface elements (splash screen, conditional API key prompt, tabbed navigation, and file upload support), ensuring an even more polished and user-friendly experience while maintaining strict security protocols.

Engineered with security, reliability, and usability at its core, SIM never persists API credentials to disk, employs a lightweight SQLite database for audit trails, and features an elegant Gradio-based graphical interface. It is ideal for developers, AI researchers, and engineering teams seeking to accelerate code maturation, reduce technical debt, and harness generative AI for continuous self-optimization.

**Repository Path**: `Self-Improve/SIM.py` within the [GRO](https://github.com/JeffStone69/GRO) project.

---

## Key Features

- **Secure API Key Management**: Credentials are sourced exclusively from environment variables (`XAI_API_KEY` or `GROK_API_KEY`) or provided transiently via the user interface. No keys are ever written to disk or committed to version control.
- **Enhanced User Interface**: Modern Gradio Blocks interface with animated splash screen, conditional visibility for API key entry, tabbed organization ("Analyze & Iterate" and "Export & Logs"), and file upload capability.
- **Autonomous Code Analysis & Refinement**: Leverages the Grok-4.3 model to process script content, uploaded files, GitHub repository files, recent error histories, and custom user feedback, returning structured explanations alongside fully executable improved scripts.
- **Persistent Logging & Auditing**: SQLite database (`xforge_self_improve.db`) records errors and improvement cycles for traceability and longitudinal performance tracking.
- **GitHub Integration**: Seamlessly fetches raw content from GitHub blob or tree URLs (including automatic resolution of common entry-point files such as `README.md`, `main.py`, or `app.py`).
- **File Upload Support**: Directly upload `.py`, `.log`, or `.txt` files for analysis.
- **Export Capabilities**: One-click CSV exports of error logs and improvement histories for external analysis or reporting.
- **Versioned Output**: Improved scripts are automatically saved with incremental versioning (e.g., `improved_script_v1.py`) to preserve iteration history.
- **Dependency Management**: Automatic, quiet installation and upgrading of required packages on first run.
- **Error Resilience**: Robust exception handling and logging ensure graceful degradation and diagnostic transparency.

---

## Architecture & Operational Flow

1. **Dependency Verification** — On launch, SIM verifies and installs required packages.
2. **Configuration Initialization** — Pydantic-validated settings load; the database schema is created if absent.
3. **Splash & Key Validation** — An elegant splash screen appears, followed by API key handling (environment variable preferred; UI fallback is memory-only).
4. **Input Ingestion** — Users supply script content, upload files, provide a GitHub URL, and/or iteration-specific instructions.
5. **Context Aggregation** — Recent errors (configurable limit), fetched GitHub content, uploaded file content, and user feedback are compiled into a concise prompt.
6. **Grok-Powered Reasoning** — A structured prompt elicits two distinct outputs: a detailed improvement rationale followed by the complete revised script (delimited by `---IMPROVED-CODE---`).
7. **Persistence & Output** — Results are logged, the improved script is saved locally, and the interface presents both explanation and code for immediate review or copy-paste.

---

## Prerequisites

- **Python**: Version 3.8 or higher (tested with 3.12).
- **Environment**: Network access to the xAI API endpoint (`https://api.x.ai/v1`).
- **API Key**: A valid xAI Grok API key. Obtain one at the [xAI Console](https://console.x.ai).

---

## Installation

### Option 1: Direct Clone (Recommended)

```bash
git clone https://github.com/JeffStone69/GRO.git
cd GRO/Self-Improve