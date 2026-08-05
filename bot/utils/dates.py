from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

def get_financial_month(current_date: date, start_day: int) -> tuple[date, date]:
    """
    Given a date and a financial month start_day, return the start and end dates 
    of the financial period that contains current_date.
    
    For example, if start_day is 15:
    - If current_date is 2024-03-20, period is 2024-03-15 to 2024-04-14.
    - If current_date is 2024-03-10, period is 2024-02-15 to 2024-03-14.
    
    If start_day is 1, it's just the normal calendar month.
    """
    # Ensure start_day is valid (1-28 to avoid edge cases with Feb)
    start_day = max(1, min(start_day, 28))
    
    if current_date.day < start_day:
        # We are in the "previous" financial month
        start_date = date(current_date.year, current_date.month, start_day) - relativedelta(months=1)
    else:
        # We are in the "current" financial month
        start_date = date(current_date.year, current_date.month, start_day)
        
    end_date = start_date + relativedelta(months=1) - timedelta(days=1)
    
    return start_date, end_date

def get_past_financial_months(current_date: date, start_day: int, count: int = 6) -> list[tuple[date, date]]:
    """
    Return a list of (start_date, end_date) tuples for the last `count` financial months,
    including the current one.
    """
    start_day = max(1, min(start_day, 28))
    
    if current_date.day < start_day:
        base_start = date(current_date.year, current_date.month, start_day) - relativedelta(months=1)
    else:
        base_start = date(current_date.year, current_date.month, start_day)
        
    periods = []
    for i in range(count):
        period_start = base_start - relativedelta(months=i)
        period_end = period_start + relativedelta(months=1) - timedelta(days=1)
        periods.append((period_start, period_end))
        
    return periods
