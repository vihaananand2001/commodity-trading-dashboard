"""
Indian Gold Price API Fetcher
Fetches live gold and silver prices from various Indian sources
"""

import requests
import json
from datetime import datetime
import time

class IndianGoldPriceAPI:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Alternative API endpoints for Indian gold prices
        self.api_endpoints = {
            'goldpricelive': 'https://api.goldpricelive.in/api/v1/prices',
            'mcx_official': 'https://www.mcxindia.com/api/v1/prices',  # May not be publicly available
            'bullion_india': 'https://www.bullionindia.com/api/prices',  # Hypothetical
            'indian_gold_api': 'https://api.indian-gold-price.com/live'  # Hypothetical
        }
    
    def fetch_from_goldpricelive(self):
        """
        Fetch prices from GoldPriceLive.in API
        """
        try:
            response = requests.get(
                self.api_endpoints['goldpricelive'], 
                headers=self.headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse the response structure
                prices = {}
                
                if 'gold' in data:
                    prices['gold_inr_per_10g'] = data['gold'].get('inr', {}).get('price', 0) / 31.1035 * 10  # Convert to per 10g
                
                if 'silver' in data:
                    prices['silver_inr_per_kg'] = data['silver'].get('inr', {}).get('price', 0) * 1000  # Convert to per kg
                
                if prices:
                    prices['source'] = 'GoldPriceLive.in'
                    prices['timestamp'] = datetime.now().isoformat()
                
                return prices
                
        except Exception as e:
            print(f"Error fetching from GoldPriceLive: {e}")
            return None
    
    def fetch_from_mcx_alternative(self):
        """
        Try to fetch from MCX alternative sources
        """
        # This would require actual MCX API access or alternative data providers
        # For now, return None as we don't have actual API access
        return None
    
    def fetch_indian_spot_prices(self):
        """
        Fetch Indian spot prices from multiple sources
        """
        sources = [
            self.fetch_from_goldpricelive,
            # Add more sources here as they become available
        ]
        
        for source_func in sources:
            try:
                prices = source_func()
                if prices:
                    return prices
            except Exception as e:
                print(f"Source failed: {e}")
                continue
        
        return None

class IndianGoldPriceScraper:
    """
    Web scraper for Indian gold price websites
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        # Indian gold price websites
        self.websites = {
            'moneymarkets': 'https://www.moneymarkets.in/gold-price/',
            'goodreturns': 'https://www.goodreturns.in/gold-rates/',
            'livemint': 'https://www.livemint.com/market/commodities',
            'economic_times': 'https://economictimes.indiatimes.com/markets/commodities'
        }
    
    def scrape_moneymarkets(self):
        """
        Scrape gold prices from MoneyMarkets.in
        """
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(self.websites['moneymarkets'], headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for gold price elements
                price_elements = soup.find_all(['span', 'div'], class_=re.compile(r'price|gold', re.I))
                
                for element in price_elements:
                    text = element.get_text(strip=True)
                    if '₹' in text and any(x in text.lower() for x in ['gold', '24k', '22k']):
                        price = self._extract_price(text)
                        if price:
                            return {
                                'gold_inr_per_10g': price,
                                'source': 'MoneyMarkets.in',
                                'timestamp': datetime.now().isoformat()
                            }
                            
        except Exception as e:
            print(f"Error scraping MoneyMarkets: {e}")
            return None
    
    def _extract_price(self, text):
        """
        Extract price value from text
        """
        import re
        
        # Look for ₹ symbol followed by numbers
        pattern = r'₹\s*([\d,]+(?:\.\d+)?)'
        match = re.search(pattern, text)
        
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        
        return None

def test_indian_gold_api():
    """
    Test the Indian gold price API
    """
    print("🔍 Testing Indian Gold Price API...")
    
    # Test API approach
    api = IndianGoldPriceAPI()
    prices = api.fetch_indian_spot_prices()
    
    if prices:
        print("✅ Successfully fetched prices from Indian API:")
        for key, value in prices.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to fetch prices from Indian API")
    
    # Test scraping approach
    scraper = IndianGoldPriceScraper()
    scraped_prices = scraper.scrape_moneymarkets()
    
    if scraped_prices:
        print("✅ Successfully scraped prices:")
        for key, value in scraped_prices.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to scrape prices")
    
    return prices or scraped_prices

if __name__ == "__main__":
    test_indian_gold_api()
