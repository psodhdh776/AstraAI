"""Plugin: show local/external IP address."""
import socket
import urllib.request

from modules.plugin_base import Plugin


class IPPlugin(Plugin):
    name = "ip_address"
    keywords = ["ip", "айпи", "мой ip", "ip адрес", "айпи адрес", "какой у меня ip", "сетевой адрес"]
    weight = 0.9
    description = "Показать IP-адрес"

    def execute(self, params, assistant):
        try:
            local = socket.gethostbyname(socket.gethostname())
        except Exception:
            local = "неизвестно"
        try:
            external = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
        except Exception:
            external = "неизвестно"
        return f"Локальный IP: {local}\nВнешний IP: {external}"


PLUGIN = IPPlugin
