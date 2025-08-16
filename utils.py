from functools import wraps
import time
from django.db import connection, OperationalError

def with_retry(max_retries=3, delay=0.1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if 'database is locked' in str(e):
                        retries += 1
                        if retries == max_retries:
                            raise
                        time.sleep(delay * (2 ** (retries - 1)))  # Exponential backoff
                        connection.close()
                    else:
                        raise
        return wrapper
    return decorator
