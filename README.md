# FOA Ingestion and Semantic Tagging Pipeline

A Python-based pipeline for ingesting Funding Opportunity Announcements (FOAs) from public sources, extracting structured fields, and applying ontology-based semantic tags. This implementation serves as a screening task for the GSOC application.

## Overview

This pipeline automates the extraction and categorization of FOAs by:

- Ingesting FOAs from Grants.gov and NSF websites
- Extracting structured fields (title, agency, dates, eligibility, description, award range)
- Applying rule-based semantic tags aligned to a controlled ontology
- Outputting normalized data in both JSON and CSV formats

## Requirements

- Python 3.7 or higher
- pip (Python package manager)

## Installation

1. Clone or download this repository

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script with a FOA URL:

```bash
python main.py --url "<URL>" --out_dir ./out
```

### Arguments

- `--url` (required): URL of the FOA to ingest (Grants.gov or NSF)
- `--out_dir` (optional): Output directory for JSON and CSV files (default: `./out`)

### Example

```bash
python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=123456" --out_dir ./out
```

## Output Format

The script generates two output files in the specified output directory:

### JSON Output (`foa.json`)

Structured JSON containing all extracted fields and semantic tags:

```json
{
  "foa_id": "FOA-123456",
  "title": "Example Funding Opportunity",
  "agency": "National Science Foundation",
  "open_date": "2024-01-01T00:00:00",
  "close_date": "2024-12-31T23:59:59",
  "eligibility_text": "Eligible applicants include...",
  "program_description": "This program supports...",
  "award_range": "$100,000 - $500,000",
  "source_url": "https://example.com/foa",
  "semantic_tags": {
    "research_domains": ["science", "engineering"],
    "methods": ["experimental", "computational"],
    "populations": ["faculty", "students"],
    "sponsor_themes": ["basic_research"]
  }
}
```

### CSV Output (`foa.csv`)

Tabular format with all fields flattened into columns. Semantic tags are joined with semicolons for compatibility with spreadsheet applications.

## Schema

### Required Fields

- `foa_id`: Unique identifier (generated if not present in URL)
- `title`: FOA title
- `agency`: Funding agency name
- `open_date`: Opening date in ISO format
- `close_date`: Closing/deadline date in ISO format
- `eligibility_text`: Eligibility requirements text
- `program_description`: Program description text
- `award_range`: Award amount range (if available)
- `source_url`: Original FOA URL

### Semantic Tags

The tagging system applies labels from a controlled ontology:

- **Research Domains**: health, engineering, science, education, environment, social
- **Methods**: experimental, computational, theoretical, field_study
- **Populations**: students, faculty, institutions, communities
- **Sponsor Themes**: basic_research, health_research, general

## Implementation Details

### Extraction Strategy

The pipeline uses HTML parsing and pattern matching to extract fields:

- **Title**: Extracted from HTML heading or title tags
- **Agency**: Identified from page content or inferred from URL domain
- **Dates**: Parsed using regex patterns and dateutil library with ISO format conversion
- **Text Fields**: Extracted from sections containing relevant keywords
- **Award Range**: Identified using regex patterns for currency amounts

### Tagging Approach

Semantic tags are applied using deterministic rule-based matching:

- Keywords from controlled vocabularies are matched against FOA text
- Multiple tags can be applied per category
- Tags are inferred from agency names when applicable

## Limitations

- Extraction accuracy depends on consistent HTML structure across sources
- Date parsing may fail with non-standard formats
- Semantic tagging is rule-based and may miss nuanced content
- PDF-based FOAs are not currently supported (HTML only)

## Testing

To test the pipeline:

1. Obtain a valid FOA URL from Grants.gov or NSF
2. Run the script with the URL
3. Verify outputs in the specified output directory

## License

This project is part of a GSOC application screening task.

## Contact

For questions about this project, please contact human-ai@cern.ch with the project title and include your CV and test results.
