import sys

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize the Limiter using the client's IP address
# Disable rate limiting during tests
is_testing = "pytest" in sys.modules

limiter = Limiter(key_func=get_remote_address, enabled=not is_testing)
