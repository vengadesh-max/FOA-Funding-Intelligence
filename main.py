#!/usr/bin/env python3
"""
FOA Ingestion and Semantic Tagging Pipeline
Screening task for GSOC application
"""

import argparse
import json
import csv
import os
import re
import sys
from urllib.parse import urlparse
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


class FOAIngester:
    """Ingests and processes Funding Opportunity Announcements (FOAs)"""
    
    def __init__(self, url: str):
        self.url = url
        self.domain = urlparse(url).netloc.lower()
        self.foa_data = {}
        
    def fetch_content(self) -> str:
        """Fetch HTML content from the URL"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch content from URL: {e}")
    
    def extract_grants_gov(self, html: str) -> Dict:
        """Extract FOA data from Grants.gov format"""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        data['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        # Extract agency
        full_text = soup.get_text()
        agency_patterns = [
            r'Agency:\s*([^\n]+)',
            r'Funding Agency:\s*([^\n]+)',
            r'Department:\s*([^\n]+)'
        ]
        agency = 'N/A'
        for pattern in agency_patterns:
            match = re.search(pattern, full_text, re.I)
            if match:
                agency = match.group(1).strip()
                break
        
        # Extract dates
        open_date = None
        close_date = None
        date_text = soup.get_text()
        
        # Look for common date patterns
        date_patterns = [
            r'Open Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Post Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Close Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Due Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text, re.I)
            if match:
                try:
                    parsed_date = date_parser.parse(match.group(1))
                    if 'open' in pattern.lower() or 'post' in pattern.lower():
                        if open_date is None:
                            open_date = parsed_date.isoformat()
                    elif 'close' in pattern.lower() or 'due' in pattern.lower():
                        if close_date is None:
                            close_date = parsed_date.isoformat()
                except (ValueError, TypeError):
                    pass
        
        # Extract eligibility text
        eligibility_keywords = ['eligibility', 'eligible', 'qualification']
        eligibility_text = self._extract_section(soup, eligibility_keywords)
        
        # Extract program description
        desc_keywords = ['description', 'summary', 'overview', 'purpose']
        program_description = self._extract_section(soup, desc_keywords)
        
        # Extract award range
        full_text = soup.get_text()
        award_patterns = [
            r'\$[\d,]+(?:\.\d+)?\s*(?:to|-)?\s*\$?[\d,]+(?:\.\d+)?',
            r'up to \$[\d,]+(?:\.\d+)?',
            r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|K)'
        ]
        award_range = None
        for pattern in award_patterns:
            match = re.search(pattern, full_text, re.I)
            if match:
                award_range = match.group(0)
                break
        
        # Generate FOA ID
        foa_id = self._generate_foa_id(data.get('title', ''), self.url)
        
        return {
            'foa_id': foa_id,
            'title': data.get('title', 'N/A'),
            'agency': agency if agency != 'N/A' else self._infer_agency_from_url(),
            'open_date': open_date or 'N/A',
            'close_date': close_date or 'N/A',
            'eligibility_text': eligibility_text or 'N/A',
            'program_description': program_description or 'N/A',
            'award_range': award_range or 'N/A',
            'source_url': self.url
        }
    
    def extract_nsf(self, html: str) -> Dict:
        """Extract FOA data from NSF format"""
        soup = BeautifulSoup(html, 'html.parser')
        data = {}
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        data['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        # NSF is always the agency
        agency = 'National Science Foundation (NSF)'
        
        # Extract dates
        open_date = None
        close_date = None
        date_text = soup.get_text()
        
        date_patterns = [
            r'Full Proposal Deadline[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Proposal Deadline[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Deadline[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Due[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text, re.I)
            if match:
                try:
                    parsed_date = date_parser.parse(match.group(1))
                    if close_date is None:
                        close_date = parsed_date.isoformat()
                except (ValueError, TypeError):
                    pass
        
        # Extract eligibility
        eligibility_text = self._extract_section(soup, ['eligibility', 'eligible', 'who may'])
        
        # Extract program description
        program_description = self._extract_section(soup, ['description', 'summary', 'overview', 'synopsis'])
        
        # Extract award range
        full_text = soup.get_text()
        award_patterns = [
            r'\$[\d,]+(?:\.\d+)?\s*(?:to|-)?\s*\$?[\d,]+(?:\.\d+)?',
            r'up to \$[\d,]+(?:\.\d+)?',
            r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|K)'
        ]
        award_range = None
        for pattern in award_patterns:
            match = re.search(pattern, full_text, re.I)
            if match:
                award_range = match.group(0)
                break
        
        foa_id = self._generate_foa_id(data.get('title', ''), self.url)
        
        return {
            'foa_id': foa_id,
            'title': data.get('title', 'N/A'),
            'agency': agency,
            'open_date': open_date or 'N/A',
            'close_date': close_date or 'N/A',
            'eligibility_text': eligibility_text or 'N/A',
            'program_description': program_description or 'N/A',
            'award_range': award_range or 'N/A',
            'source_url': self.url
        }
    
    def _extract_section(self, soup: BeautifulSoup, keywords: List[str]) -> Optional[str]:
        """Extract text from a section containing keywords"""
        text = soup.get_text()
        for keyword in keywords:
            # Escape special regex characters in keyword
            escaped_keyword = re.escape(keyword)
            pattern = re.compile(rf'{escaped_keyword}[:\s]*([^\n]+(?:\n[^\n]+)*)', re.I)
            match = re.search(pattern, text)
            if match:
                section = match.group(1).strip()
                # Limit to reasonable length
                if len(section) > 500:
                    section = section[:500] + '...'
                return section
        return None
    
    def _generate_foa_id(self, title: str, url: str) -> str:
        """Generate a unique FOA ID"""
        # Try to extract ID from URL first
        url_id_match = re.search(r'/(\d+)/', url)
        if url_id_match:
            return f"FOA-{url_id_match.group(1)}"
        
        # Generate from title hash
        title_hash = abs(hash(title)) % 100000
        return f"FOA-{title_hash}"
    
    def _infer_agency_from_url(self) -> str:
        """Infer agency name from URL"""
        if 'grants.gov' in self.domain:
            return 'Grants.gov'
        elif 'nsf.gov' in self.domain:
            return 'National Science Foundation (NSF)'
        elif 'nih.gov' in self.domain:
            return 'National Institutes of Health (NIH)'
        else:
            return 'Unknown Agency'
    
    def ingest(self) -> Dict:
        """Main ingestion method"""
        html = self.fetch_content()
        
        if 'nsf.gov' in self.domain:
            self.foa_data = self.extract_nsf(html)
        else:
            self.foa_data = self.extract_grants_gov(html)
        
        return self.foa_data


class SemanticTagger:
    """Applies semantic tags to FOA data using rule-based approach"""
    
    # Controlled ontology for tagging
    RESEARCH_DOMAINS = {
        'health': ['health', 'medical', 'clinical', 'biomedical', 'disease', 'treatment', 'therapy'],
        'engineering': ['engineering', 'technology', 'innovation', 'design', 'manufacturing'],
        'science': ['science', 'research', 'discovery', 'experiment', 'laboratory'],
        'education': ['education', 'learning', 'teaching', 'student', 'curriculum'],
        'environment': ['environment', 'climate', 'sustainability', 'energy', 'renewable'],
        'social': ['social', 'community', 'society', 'behavior', 'policy', 'public']
    }
    
    METHODS = {
        'experimental': ['experiment', 'trial', 'testing', 'laboratory', 'empirical'],
        'computational': ['computational', 'modeling', 'simulation', 'algorithm', 'data analysis'],
        'theoretical': ['theoretical', 'theory', 'mathematical', 'conceptual'],
        'field_study': ['field study', 'fieldwork', 'survey', 'observation', 'ethnographic']
    }
    
    POPULATIONS = {
        'students': ['student', 'undergraduate', 'graduate', 'postdoctoral'],
        'faculty': ['faculty', 'professor', 'researcher', 'investigator'],
        'institutions': ['institution', 'university', 'college', 'organization'],
        'communities': ['community', 'public', 'population', 'society']
    }
    
    def tag(self, foa_data: Dict) -> Dict:
        """Apply semantic tags to FOA data"""
        text = f"{foa_data.get('title', '')} {foa_data.get('program_description', '')} {foa_data.get('eligibility_text', '')}".lower()
        
        tags = {
            'research_domains': [],
            'methods': [],
            'populations': [],
            'sponsor_themes': []
        }
        
        # Tag research domains
        for domain, keywords in self.RESEARCH_DOMAINS.items():
            if any(keyword in text for keyword in keywords):
                tags['research_domains'].append(domain)
        
        # Tag methods
        for method, keywords in self.METHODS.items():
            if any(keyword in text for keyword in keywords):
                tags['methods'].append(method)
        
        # Tag populations
        for population, keywords in self.POPULATIONS.items():
            if any(keyword in text for keyword in keywords):
                tags['populations'].append(population)
        
        # Sponsor themes (infer from agency)
        agency = foa_data.get('agency', '').lower()
        if 'nsf' in agency:
            tags['sponsor_themes'].append('basic_research')
        elif 'nih' in agency:
            tags['sponsor_themes'].append('health_research')
        else:
            tags['sponsor_themes'].append('general')
        
        foa_data['semantic_tags'] = tags
        return foa_data


def save_json(data: Dict, output_path: str):
    """Save FOA data as JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_csv(data: Dict, output_path: str):
    """Save FOA data as CSV"""
    # Flatten semantic tags for CSV
    csv_row = {
        'foa_id': data.get('foa_id', ''),
        'title': data.get('title', ''),
        'agency': data.get('agency', ''),
        'open_date': data.get('open_date', ''),
        'close_date': data.get('close_date', ''),
        'eligibility_text': data.get('eligibility_text', ''),
        'program_description': data.get('program_description', ''),
        'award_range': data.get('award_range', ''),
        'source_url': data.get('source_url', ''),
        'research_domains': '; '.join(data.get('semantic_tags', {}).get('research_domains', [])),
        'methods': '; '.join(data.get('semantic_tags', {}).get('methods', [])),
        'populations': '; '.join(data.get('semantic_tags', {}).get('populations', [])),
        'sponsor_themes': '; '.join(data.get('semantic_tags', {}).get('sponsor_themes', []))
    }
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_row.keys())
        writer.writeheader()
        writer.writerow(csv_row)


def main():
    parser = argparse.ArgumentParser(
        description='FOA Ingestion and Semantic Tagging Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='URL of the FOA to ingest (Grants.gov or NSF)'
    )
    parser.add_argument(
        '--out_dir',
        type=str,
        default='./out',
        help='Output directory for JSON and CSV files (default: ./out)'
    )
    
    args = parser.parse_args()
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(args.out_dir, exist_ok=True)
        
        # Ingest FOA
        ingester = FOAIngester(args.url)
        foa_data = ingester.ingest()
        
        # Apply semantic tags
        tagger = SemanticTagger()
        foa_data = tagger.tag(foa_data)
        
        # Save outputs
        json_path = os.path.join(args.out_dir, 'foa.json')
        csv_path = os.path.join(args.out_dir, 'foa.csv')
        
        save_json(foa_data, json_path)
        save_csv(foa_data, csv_path)
        
        print(f"Successfully processed FOA: {foa_data.get('foa_id')}")
        print(f"JSON saved to: {json_path}")
        print(f"CSV saved to: {csv_path}")
        
    except Exception as e:
        print(f"Error processing FOA: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
