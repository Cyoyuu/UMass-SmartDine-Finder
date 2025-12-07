# UMass-SmartDine-Finder
CS 520 — Final Project

## Overview
UMass-SmartDine-Finder is a Django-based project that uses large language models to help users search UMass dining locations more intelligently. This README covers environment setup, LLM configuration, and how to run the server.

---

## Installation

Clone the repository:

```
git clone --recursive https://github.com/Cyoyuu/UMass-SmartDine-Finder.git
```

**Or, if you already cloned:**

```
git submodule update --init --recursive
```

## Environment Setup

You may use **conda** or **venv**.

### Step 1 Option A — Conda

```bash
conda env create -f env.yml
conda activate umass_dining
```

### Step 1 Option B — Python venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip django
pip install psycopg2 openai bs4 pint requests
```

### Step 2

Set up `umass-toolkit`.

```
cd umass-toolkit
python setup.py install
cd ..
```

---

## LLM Configuration

Before running the server, modify `lm_config.json`:

```
{
    "lm_source": "openai", # supported source includes ["openai", "openrouter", "azure", "dashscope"]
    "lm_id": "gpt-4o-mini"
}
```

### Supported Configuration

| lm_source  | Example lm_id        |
| ---------- | -------------------- |
| openai     | "gpt-4o-mini"        |
| openrouter | "openai/gpt-4o-mini" |
| azure      | "gpt-4o"             |
| dashscope  | "qwen-turbo"         |

### API Keys

Export API keys based on your provider:

```bash
export OPENAI_API_KEY="YOUR_KEY"
export OPENROUTER_API_KEY="YOUR_KEY"
export DASHSCOPE_API_KEY="YOUR_KEY"
```

For **Azure OpenAI**, store credentials in `.api_keys.json`:

```json
{
  "embedding": [
    {
      "AZURE_ENDPOINT": "YOUR_ENDPOINT",
      "OPENAI_API_KEY": "YOUR_KEY"
    }
  ],
  "all": [
    {
      "AZURE_ENDPOINT": "YOUR_ENDPOINT",
      "OPENAI_API_KEY": "YOUR_KEY"
    }
  ]
}
```

---

## Run the Server

Make sure dependencies are installed and API keys are configured. Then:

```bash
python manage.py migrate
python manage.py runserver
```

---

## Troubleshooting

### psycopg2 installation issue on macOS

If `psycopg2` fails to install:

```bash
pip install psycopg2-binary
```