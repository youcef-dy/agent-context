"""Credential-free private network check; run inside the Hermes container."""

from urllib.request import urlopen


with urlopen('http://adam-hindsight:8888/health', timeout=8) as response:
    print('hindsight_health_from_hermes_http=' + str(response.status))
