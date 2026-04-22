from crewai.tools import BaseTool
import json
import sys
import os

# Ensure the root project directory is in the path so we can import tools.scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.scraper import AxessoScraper

class AmazonScraperTool(BaseTool):
    name: str = "Amazon Product Scraper Tool"
    description: str = "Use this tool to extract Amazon product descriptions, reviews, and specs for a given ASIN."
    
    def _run(self, asin: str) -> str:
        scraper = AxessoScraper()
        result = scraper.get_product_details(asin)
        if result:
            # Clean string version for LLM context
            return json.dumps(result)[:5000] 
        return f"Failed to retrieve Amazon data for ASIN {asin}."

