"""
Arihant Spot Price Fetcher
Fetches live gold and silver prices from Arihant Spot website
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time

class ArihantSpotFetcher:
    def __init__(self):
        self.base_url = "https://arihantspot.in"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def fetch_prices(self):
        """
        Fetch live prices from Arihant Spot website
        Returns dict with gold and silver prices in INR
        """
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for price elements
            prices = self._extract_prices(soup)
            
            if prices:
                prices['source'] = 'Arihant Spot'
                prices['timestamp'] = datetime.now().isoformat()
                prices['url'] = self.base_url
                
            return prices
            
        except Exception as e:
            print(f"Error fetching Arihant Spot prices: {e}")
            return None
    
    def _extract_prices(self, soup):
        """
        Extract gold and silver prices from the HTML content
        """
        prices = {}
        
        # Method 1: Look for specific price containers
        price_containers = soup.find_all(['div', 'span', 'td'], class_=re.compile(r'price|gold|silver', re.I))
        
        for container in price_containers:
            text = container.get_text(strip=True)
            
            # Look for gold prices
            if 'gold' in text.lower() and '₹' in text:
                gold_price = self._extract_price_value(text)
                if gold_price:
                    prices['gold_inr_per_10g'] = gold_price
                    
            # Look for silver prices  
            if 'silver' in text.lower() and '₹' in text:
                silver_price = self._extract_price_value(text)
                if silver_price:
                    prices['silver_inr_per_kg'] = silver_price
        
        # Method 2: Look for JavaScript variables
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for price variables in JavaScript
                js_prices = self._extract_js_prices(script.string)
                prices.update(js_prices)
        
        # Method 3: Look for meta tags or data attributes
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            if meta.get('name') and 'price' in meta.get('name', '').lower():
                content = meta.get('content', '')
                if 'gold' in content.lower():
                    gold_price = self._extract_price_value(content)
                    if gold_price:
                        prices['gold_inr_per_10g'] = gold_price
                elif 'silver' in content.lower():
                    silver_price = self._extract_price_value(content)
                    if silver_price:
                        prices['silver_inr_per_kg'] = silver_price
        
        return prices
    
    def _extract_price_value(self, text):
        """
        Extract numeric price value from text
        """
        # Look for ₹ symbol followed by numbers
        patterns = [
            r'₹\s*([\d,]+(?:\.\d+)?)',
            r'Rs\.?\s*([\d,]+(?:\.\d+)?)',
            r'price[:\s]*([\d,]+(?:\.\d+)?)',
            r'rate[:\s]*([\d,]+(?:\.\d+)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    return float(price_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_js_prices(self, js_content):
        """
        Extract prices from JavaScript content
        """
        prices = {}
        
        # Look for common JavaScript variable patterns
        patterns = [
            r'var\s+goldPrice\s*=\s*([\d,]+(?:\.\d+)?)',
            r'var\s+silverPrice\s*=\s*([\d,]+(?:\.\d+)?)',
            r'goldPrice[:\s]*([\d,]+(?:\.\d+)?)',
            r'silverPrice[:\s]*([\d,]+(?:\.\d+)?)',
            r'"gold"[:\s]*([\d,]+(?:\.\d+)?)',
            r'"silver"[:\s]*([\d,]+(?:\.\d+)?)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, js_content, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match.replace(',', ''))
                    
                    if 'gold' in pattern.lower():
                        prices['gold_inr_per_10g'] = price
                    elif 'silver' in pattern.lower():
                        prices['silver_inr_per_kg'] = price
                        
                except ValueError:
                    continue
        
        return prices

def test_arihant_fetcher():
    """
    Test the Arihant Spot price fetcher
    """
    print("🔍 Testing Arihant Spot Price Fetcher...")
    
    fetcher = ArihantSpotFetcher()
    prices = fetcher.fetch_prices()
    
    if prices:
        print("✅ Successfully fetched prices from Arihant Spot:")
        for key, value in prices.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to fetch prices from Arihant Spot")
    
    return prices

if __name__ == "__main__":
    test_arihant_fetcher()
