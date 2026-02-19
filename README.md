# FOA Ingestion and Semantic Tagging Pipeline

A Python script that ingests Funding Opportunity Announcements (FOAs) from Grants.gov or NSF, extracts structured fields, and applies semantic tags.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py --url "<URL>" --out_dir ./out
```

**Arguments:**
- `--url` (required): URL of the FOA to ingest
- `--out_dir` (optional): Output directory (default: `./out`)

**Example:**
```bash
python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=123456" --out_dir ./out
```

## Output

The script generates two files in the output directory:

- `foa.json` - Structured JSON with all extracted fields and semantic tags
- `foa.csv` - Tabular format with flattened fields

### Extracted Fields

- FOA ID, Title, Agency
- Open/Close dates (ISO format)
- Eligibility text, Program description
- Award range (if available)
- Source URL

### Semantic Tags

- Research domains (health, engineering, science, education, environment, social)
- Methods (experimental, computational, theoretical, field_study)
- Populations (students, faculty, institutions, communities)
- Sponsor themes (basic_research, health_research, general)

## Contact

For questions, contact human-ai@cern.ch with the project title and include your CV and test results.
