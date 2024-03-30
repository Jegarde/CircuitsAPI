import aiohttp
from aiohttp.client_exceptions import ServerDisconnectedError

class Request:
    def __init__(self, session: aiohttp.ClientSession, method: str, url: str, payload: str | dict = {}):
        # aiohttp session
        self.session = session

        # Request
        self.method = method
        self.url = url
        self.payload = payload

        # Attempts if failed
        self.attempts = 0
        self.max_attempts = 3

    async def send_request(self):
        """Sends an API request with a retry system

        Args:
            method (str): Call method (get, put)
            url (str): API host + endpoint
            payload (str | dict): Optional data

        Raises:
            InvalidMethod: If method argument is not supported
        """
        try:
            resp = await self.session.request(method=self.method, url=self.url, data=self.payload)
            return resp
        except ServerDisconnectedError:
            if self.attempts >= self.max_attempts:
                print("Failed to make request.")
                return None

            print("Server disconnected, attempting again...")
            self.attempts += 1
            resp = await self.send_request(self.method, self.url, self.payload)
        except Exception as e:
            # Unhandled error
            print(f"Error sending request METHOD: {self.method} URL: {self.url} PAYLOAD: {self.payload}")
            raise e