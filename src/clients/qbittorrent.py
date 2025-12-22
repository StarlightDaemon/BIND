import qbittorrentapi
import logging
import os

logger = logging.getLogger("Downloader")

class DownloaderClient:
    def add_magnet(self, magnet_link, category=None):
        raise NotImplementedError

class QBittorrentClient(DownloaderClient):
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        
    def connect(self):
        try:
            self.client = qbittorrentapi.Client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
            self.client.auth_log_in()
            logger.info(f"Connected to qBittorrent at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
            self.client = None

    def add_magnet(self, magnet_link, category="ABMG"):
        if not self.client:
            self.connect()
            
        if self.client:
            try:
                self.client.torrents_add(urls=magnet_link, category=category)
                logger.info(f"Sent magnet to qBittorrent")
                return True
            except Exception as e:
                logger.error(f"Failed to add torrent: {e}")
        return False
