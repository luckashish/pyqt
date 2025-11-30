"""Economic Calendar Data Provider - provides dummy calendar events."""
from datetime import datetime, timedelta
from typing import List
import random

from data.models import CalendarEvent


class CalendarProvider:
    """Provides economic calendar data (dummy for demo)."""
    
    def __init__(self):
        self._event_templates = [
            ("USD", "Non-Farm Payrolls", "high"),
            ("USD", "Federal Reserve Interest Rate Decision", "high"),
            ("USD", "CPI (Consumer Price Index)", "high"),
            ("USD", "Retail Sales", "medium"),
            ("EUR", "ECB Interest Rate Decision", "high"),
            ("EUR", "German GDP", "medium"),
            ("EUR", "Eurozone CPI", "high"),
            ("GBP", "BOE Interest Rate Decision", "high"),
            ("GBP", "UK Employment Change", "medium"),
            ("GBP", "UK GDP", "medium"),
            ("JPY", "BOJ Interest Rate Decision", "high"),
            ("JPY", "Japan CPI", "medium"),
            ("AUD", "RBA Interest Rate Decision", "high"),
            ("CAD", "BOC Interest Rate Decision", "high"),
            ("CHF", "SNB Interest Rate Decision", "high"),
        ]
    
    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        """
        Get upcoming economic calendar events.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of CalendarEvent objects
        """
        events = []
        
        # Generate events for next N days
        for day in range(days):
            # 2-4 events per day
            num_events = random.randint(2, 4)
            
            for _ in range(num_events):
                currency, event_name, impact = random.choice(self._event_templates)
                
                # Random time during the day
                event_date = datetime.now() + timedelta(days=day)
                event_date = event_date.replace(
                    hour=random.randint(8, 16),
                    minute=random.choice([0, 30]),
                    second=0,
                    microsecond=0
                )
                
                # Generate forecast and previous values
                base_value = random.uniform(0.1, 5.0)
                forecast = f"{base_value:.1f}%"
                previous = f"{base_value + random.uniform(-0.5, 0.5):.1f}%"
                
                event = CalendarEvent(
                    date=event_date,
                    currency=currency,
                    event=event_name,
                    impact=impact,
                    forecast=forecast,
                    previous=previous,
                    actual=""  # Will be filled when event occurs
                )
                
                events.append(event)
        
        # Sort by date
        events.sort(key=lambda x: x.date)
        
        return events
    
    def get_next_high_impact_event(self) -> CalendarEvent:
        """Get the next high-impact event."""
        all_events = self.get_upcoming_events(7)
        high_impact = [e for e in all_events if e.impact == "high" and e.date > datetime.now()]
        
        if high_impact:
            return high_impact[0]
        
        # Return first event if no high impact found
        return all_events[0] if all_events else None


# Global calendar provider instance
calendar_provider = CalendarProvider()
