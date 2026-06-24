"""
Home Assistant integration via REST API.
"""
import json
import logging
import urllib.request
import urllib.error
import ssl

logger = logging.getLogger("Astra.HomeAssistant")

DEFAULT_URL = "http://192.168.1.100:8123"
DEFAULT_TOKEN = ""


class HomeAssistant:
    def __init__(self, url=DEFAULT_URL, token=DEFAULT_TOKEN):
        self.url = url.rstrip("/")
        self.token = token
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    def set_config(self, url, token):
        self.url = url.rstrip("/")
        self.token = token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, data=None):
        try:
            req = urllib.request.Request(
                f"{self.url}/api/{path}",
                data=json.dumps(data).encode() if data else None,
                headers=self._headers(),
                method=method,
            )
            with urllib.request.urlopen(req, timeout=10, context=self._ctx) as r:
                return json.loads(r.read())
        except Exception as e:
            logger.debug("HA request: %s", e)
            return None

    def get_states(self):
        return self._request("GET", "states")

    def get_entities(self, domain=None):
        states = self._request("GET", "states") or []
        if domain:
            return [s for s in states if s.get("entity_id", "").startswith(domain)]
        return states

    def call_service(self, domain, service, **data):
        return self._request("POST", f"services/{domain}/{service}", data)

    def turn_on(self, entity_id):
        domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
        return self.call_service(domain, "turn_on", entity_id=entity_id)

    def turn_off(self, entity_id):
        domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
        return self.call_service(domain, "turn_off", entity_id=entity_id)

    def get_weather(self):
        states = self._request("GET", "states") or []
        weather = [s for s in states if s.get("entity_id", "").startswith("weather.")]
        return weather[0] if weather else None

    def get_sensor(self, entity_id):
        data = self._request("GET", f"states/{entity_id}")
        return data


_global = HomeAssistant()
