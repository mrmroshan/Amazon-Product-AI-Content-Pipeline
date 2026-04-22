import os
import requests
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AxessoScraper:
    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = os.getenv("RAPIDAPI_HOST", "axesso-axesso-amazon-data-service-v1.p.rapidapi.com")
        
        if not self.api_key:
            logging.warning("RAPIDAPI_KEY is missing from environment variables. Scraper will fail.")

        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }
        
    def get_product_details(self, asin: str, country_code: str = "US") -> Optional[Dict[str, Any]]:
        """
        Fetches basic product details and reviews for a given ASIN.
        For phase 1, we extract basic info that Agent A (Forensic Researcher) will dissect.
        """
        url = f"https://{self.host}/amz/amazon-lookup-product"
        querystring = {"url": f"https://www.amazon.com/dp/{asin}/"}

        logging.info(f"Fetching product details for ASIN: {asin}")
        
        try:
            response = requests.get(url, headers=self.headers, params=querystring, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data for ASIN {asin}: {e}")
            return None

# Simple testing block running only if script is executed directly
if __name__ == "__main__":
    scraper = AxessoScraper()
    test_asin = "B0CFN6GRTH" # User provided ASIN
    print(f"Testing Scraper for ASIN: {test_asin}")
    result = scraper.get_product_details(test_asin)
    if result:
        print("Success! Retrieved data payload snippet:")
        print(str(result)[:500] + "...") # Print just a snippet
    else:
        print("Failed to get data. (Make sure you set your RAPIDAPI_KEY in .env)")
