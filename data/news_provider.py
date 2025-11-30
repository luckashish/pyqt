"""Market News Data Provider - provides dummy news data."""
from datetime import datetime, timedelta
from typing import List
import random

from data.models import NewsItem


class NewsProvider:
    """Provides market news data (dummy for demo)."""
    
    def __init__(self):
        self._news_templates = [
            ("Fed Holds Interest Rates Steady", "Reuters", "high", "USD"),
            ("ECB Signals Potential Rate Cut", "Bloomberg", "high", "EUR"),
            ("UK GDP Growth Exceeds Expectations", "Financial Times", "medium", "GBP"),
            ("Japan's Core Inflation Rises", "Nikkei", "medium", "JPY"),
            ("US Jobs Report Shows Strong Gains", "CNBC", "high", "USD"),
            ("Eurozone Manufacturing PMI Declines", "MarketWatch", "medium", "EUR"),
            ("BOE Minutes Show Dovish Tone", "Reuters", "medium", "GBP"),
            ("Australia Unemployment Rate Falls", "Bloomberg", "low", "AUD"),
            ("Swiss Franc Strengthens on Safe Haven Demand", "FX Street", "low", "CHF"),
            ("Canadian Retail Sales Disappoint", "BNN Bloomberg", "medium", "CAD"),
        ]
    
    def get_latest_news(self, count: int = 20) -> List[NewsItem]:
        """
        Get latest market news.
        
        Args:
            count: Number of news items to return
            
        Returns:
            List of NewsItem objects
        """
        news_items = []
        
        for i in range(count):
            # Select random template
            headline, source, impact, currency = random.choice(self._news_templates)
            
            # Create news item with recent timestamp
            timestamp = datetime.now() - timedelta(hours=random.randint(0, 48))
            
            news_item = NewsItem(
                headline=headline,
                source=source,
                timestamp=timestamp,
                impact=impact,
                currency=currency,
                content=f"Full content for: {headline}. This is a detailed article about market movements and economic impacts..."
            )
            
            news_items.append(news_item)
        
        # Sort by timestamp (newest first)
        news_items.sort(key=lambda x: x.timestamp, reverse=True)
        
        return news_items


# Global news provider instance
news_provider = NewsProvider()
