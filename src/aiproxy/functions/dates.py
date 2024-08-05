from typing import Annotated, Callable
import datetime

def today() -> str:
    """
    Returns todays date in ISO date format
    """
    return datetime.date.today().isoformat()

def date_in_days(
        days:Annotated[int, "The number of days from today to return the date for"]
    ) -> str:
    """
    Returns the date for a number of days from today in ISO date format
    """
    return (datetime.date.today() + datetime.timedelta(days=int(days))).isoformat()

def dayname_for_date(
        date:Annotated[str, "Return the name of the day (eg. Monday) for the provided date. The date shold be in ISO date format (YYYY-MM-DD)"]
    ) -> str:
    """
    Returns the day name for a date in ISO date format
    """
    return datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%A")


def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("today", "Returns todays date in ISO date format (YYYY-MM-DD)", today)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("date_in_days", "Returns the date for a number of days from today in ISO date format (YYYY-MM-DD)", date_in_days)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("dayname_for_date", "Return the day of the week (eg. Monday) for the provided date. The date provided shold be in ISO date format (YYYY-MM-DD)", dayname_for_date)
