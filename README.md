# WoundQuant

**Algorithmic Wound Tissue Quantification Software**

WoundQuant is a deterministic, offline-first desktop application designed to quantify wound tissue composition without requiring cloud connectivity, GPUs, or heavy deep-learning runtimes. Built by **My Technical Romance** at Far Eastern University Institute of Technology, the system prioritizes speed, reproducibility, and low hardware overhead for resource-constrained clinical environments.

## Key Features

- **Deterministic Tissue Segmentation:** Uses integer-based HSV color-space conversion to classify and quantify wound tissue regions consistently across runs.
- **Offline-First Architecture:** Operates entirely locally with zero external API calls, preserving patient data privacy and reliability in offline clinics.
- **Standalone Deployment:** Packaged as a self-contained desktop executable using PyInstaller for straightforward installation on standard Windows machines.
- **Clinically Validated Workflow:** Reviewed and validated in consultation with a specialist surgeon to align tissue quantification outputs with practical clinical assessment.

## Performance Benchmarks

Evaluated through automated batch testing:

| Metric | Measured Result |
| :--- | :--- |
| **Processing Latency** | ~0.02 seconds per image |
| **Memory Footprint** | 91.32 MB RAM |
| **Peak CPU Utilization** | 37.21% |

## Tech Stack

- **Language:** Python
- **Core Algorithms:** Integer-Based HSV Color-Space Conversion & Image Processing
- **Packaging & Profiling:** PyInstaller, `psutil`

## Getting Started

1. Clone this repository and enter the project directory:
   ```bash
   cd WoundQuant
   pip install -r requirements.txt
   python main.py

Team
Devrick Atok — Project Leader

Adrian Flores — Developer

Adrian Sevilla — Developer

Peter Navas — Developer
