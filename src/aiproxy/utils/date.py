from time import strftime, localtime, time
from datetime import datetime

ISO_STRING_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
ISO_STRING_FORMAT_NOTZ = "%Y-%m-%dT%H:%M:%S"
SHORT_YMD_FORMAT = "%Y%m%d"

def now() -> datetime:
    return datetime.now()

def now_secs() -> int:
    return int(time())

def now_millis() -> int:
    return int(time() * 1000)

def now_as_str() -> str:
   return strftime(ISO_STRING_FORMAT, localtime())

def datetime_from_str(iso_str:str) -> datetime:
    try:
        return datetime.strptime(iso_str, ISO_STRING_FORMAT)
    except:
        return datetime.strptime(iso_str, ISO_STRING_FORMAT_NOTZ)   ## Some of the dates have no TZ, so parse without

def datetime_from_millis(millis:int) -> datetime:    
    return datetime.fromtimestamp(millis/1000.0)

def datetime_to_str(dt:datetime) -> str:
    return dt.strftime(ISO_STRING_FORMAT)

def datetime_to_millis(dt:datetime) -> int:
    return int(dt.timestamp() * 1000)

def millis_to_str(millis:int) -> str:
    return datetime_from_millis(millis).strftime(ISO_STRING_FORMAT)

def datetime_from_short_ymd_str(short_ymd:str) -> datetime:    
    """
    Returns a datetime from a date string in the format: "yyyMMdd"
    """
    return datetime.strptime(short_ymd, SHORT_YMD_FORMAT)