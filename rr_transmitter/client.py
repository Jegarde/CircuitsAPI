import asyncio
import aiohttp
import recnetpy
import time
from typing import Optional, List
from dataclasses import dataclass
from recnetpy.dataclasses.account import Account
from .helpers import *
from .exceptions import *


@dataclass
class LoginCookie:
    csrf_token: str
    session_token: str

class Client:
    def __init__(self, dev_token: str, rr_token: LoginCookie):
        # Dev token
        self.dev_token = dev_token

        # Headers & cookies
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        self.cookies = {}

        # Determine login method
        if isinstance(rr_token, LoginCookie):
            # Cookie login method
            self.cookies = {"__Host-next-auth.csrf-token": rr_token.csrf_token, "__Secure-next-auth.session-token": rr_token.session_token}
            self.cookie_method = True
        else:
            self.headers["Authorization"] = "Bearer " + rr_token
            self.cookie_method = False

        # clients
        self.session: aiohttp.ClientSession | None = None
        self.RecNet: recnetpy.Client | None = None

        # Initialized
        self.initialized = False

    async def initialize(self):
        if self.initialized: return
        
        self.session = aiohttp.ClientSession(headers=self.headers, cookies=self.cookies)
        self.RecNet = recnetpy.Client(api_key=self.dev_token)

        # Check if logged in with cookie
        if self.cookie_method:
            # Get access token
            resp = await self.session.get("https://rec.net/api/auth/session")
            data = await resp.json()
            token = data.get("accessToken")
            assert token, "Couldn't login!"
            self.session.headers["Authorization"] = "Bearer " + token

        self.initialized = True


    async def connect_to_room(self, room: str | int):
        conn: RoomConnection = RoomConnection(room, self)
        await conn.initialize()
        return conn
    

    async def close(self) -> None:
        await self.session.close()
        await self.RecNet.close()


class RoomConnection:
    def __init__(self, room: str | int, client: Client):
        self.client = client

        # Room ID to establish connection to
        self.room_id = room                                     

        # Dev token
        self.dev_token = self.client.dev_token

        # Roles
        self.roles = {}

        # clients
        self.session: aiohttp.ClientSession = self.client.session
        self.RecNet: recnetpy.Client = self.client.RecNet


    async def initialize(self):
        resp = await self.session.get(f"https://rooms.rec.net/rooms/{self.room_id}/roles/")
        roles = await resp.json()
        if roles == []: raise RoomNotFound

        self.roles = await resp.json()
        

    async def connect_to_user(self, user: str | int):
        # Find user
        if isinstance(user, int):
            account = await self.RecNet.accounts.fetch(user)
        else:
            account = await self.RecNet.accounts.get(user)
        if not account: raise UserNotFound

        return UserConnection(account=account, room_connection=self)


    async def find_players(self) -> Optional[List[dict]]:
        # Finds players in the room from images
        resp = await self.session.get(f"https://apim.rec.net/apis/api/images/v4/room/{self.room_id}?take=10")
        if resp.status != 200: return []

        # Find players in room from images
        player_ids = []
        image_data = await resp.json()
        for i in image_data:
            # Ignore images over 10 minutes old
            if time.time() - date_to_unix(i["CreatedAt"]) >= 600:
                break

            # Player who took the pic
            if i["PlayerId"] not in player_ids:
                player_ids.append(i["PlayerId"])

            # Any possible tagged players
            for j in i["TaggedPlayerIds"]:
                if j not in player_ids:
                    player_ids.append(j)

        return player_ids



    async def close(self) -> None:
        await self.session.close()
        await self.RecNet.close()


class UserConnection:
    def __init__(self, account: Account, room_connection: RoomConnection):
        # Room connection
        self.room_conn = room_connection

        # Room ID
        self.room_id = self.room_conn.room_id

        # Connected account
        self.account = account

        # aiohttp session
        self.session = self.room_conn.session

        # previous role
        self.previous_role: int = self.__get_current_role()

        # available characters
        self.characters = supported_characters()


    # Packet Handler dependency functions

    async def send_text_packet(self, text: str):
        """Sends a text packet

        REQUIREMENTS:   
            - 'Receiver' circuit board must be connected to 'Packet Handler' circuit board for the packet to be decoded.
            - 'Decimal to Character' circuit board must be used to convert packet to the corresponding character.

        Args:
            text (str): Text to transmit
        """
        chars = [*text]
        packets = []
        for c in chars:
            if c in self.characters:
                packets.append(
                    int(f"{self.characters.index(c):b}")
                )

        # Transmit packet count
        packet_count = len(packets)
        await self.__transmit_packet_count(packet_count)
        print(f"Packet count: {packet_count}")

        # Transmit packets
        for i, packet in enumerate(packets, start=1):
            await self.__transmit_packet(packet)
            print(f"Packet {i}/{len(packets)} - bits: {packet} - int: {int(str(packet), 2)}")

        # Done!
            

    async def send_int_packet(self, packet: int):
        """Sends an integer packet

        Requires 'Receiver' circuit board to be connected to 'Packet Handler' circuit board to be decoded.

        Args:
            packet (int): Integer to transmit
        """

        # Transmit packet count
        packet_count = 1
        await self.__transmit_packet_count(packet_count)
        print(f"Packet count: {packet_count}")

        # Transmit packet
        await self.__transmit_packet(int(f"{packet:b}"))
        print(f"Packet {packet} - bits: {int(f"{packet:b}")} SENT!")

        # Done!


    async def ping(self) -> bool:
        """Attempts to ping the connected user. Waits a second for a pong.

        Requires 'Receiver' circuit board to be connected to 'Packet Handler' circuit board to be received.

        Returns:
            bool: Received pong?
        """
        instance = await self.get_instance()

        # Check if user is in the specified room
        if instance == None or instance.get("roomId") != self.room_id: return False

        # Get the matchmaking state which will be updated as a pong
        matchmaking_state = instance.get("matchmakingPolicy")

        # Ping the user
        await self.transmit_packet(0)

        # Wait for a response
        await asyncio.sleep(1)

        # Check for a response
        instance = await self.get_instance()

        # Check if user is in the specified room
        if instance == None or instance.get("roomId") != self.room_id: return False

        # Check for a pong
        return matchmaking_state != instance.get("matchmakingPolicy")


    #Low level functions

    async def send_bit_0(self):
        """Executes 'Bit 0' port in 'Receiver' circuit board
        """

        await self.__transmit_bit(0)


    async def send_bit_1(self):
        """Executes 'Bit 1' port in 'Receiver' circuit board
        """

        await self.__transmit_bit(1)


    async def send_end_signal(self):
        """Executes 'END' port in 'Receiver' circuit board
        """

        await self.__packet_completed(self)
                

    async def send_binary(self, binary: int):
        """Sends a binary number executing 'Bit 1' and 'Bit 0' ports in 'Receiver' circuit board.
        Once the binary number has been fully sent, 'END' port will be executed.

        Args:
            binary (int): Binary number (ex. 1010100)
        """
        await self.__transmit_packet(binary)


    async def get_instance(self) -> dict | None:
        """Returns the instance connected players is in

        Returns:
            dict | None: Instance data if successful
        """
        resp = await self.session.get(f"https://match.rec.net/player?id={self.account.id}")
        if resp.status != 200: return None
        
        # Get user's current instance
        data = await resp.json()
        instance = data[0].get("roomInstance")
        if not instance: return None

        return instance
    

    # Backend functions

    def __get_current_role(self) -> int:
        for i in self.room_conn.roles:
            if i["AccountId"] == self.account.id:
                return str(i["Role"])
        return "0"
    

    async def __transmit_packet(self, binary: int):
        bits = [*str(binary)]
        bits.reverse()
        for bit in bits:
            await self.__transmit_bit(int(bit))
        await self.__packet_completed()


    async def __transmit_packet_count(self, content_length: int):
        await self.__transmit_packet(int(f"{content_length:b}"))


    async def __packet_completed(self) -> bool:
        payload = "role="

        # Check if it's the same bit as before
        if self.previous_role == "0":
            role_id = "25"
        else:
            role_id = "0"

        payload += role_id
        self.previous_role = role_id

        resp = await self.session.put(f"https://rooms.rec.net/rooms/{self.room_id}/roles/{self.account.id}", data=payload)
        return resp.status == 200

    async def __transmit_bit(self, bit: int) -> bool:
        bit_keys = {
            0: "20",
            1: "10"
        }

        """
        none - id 0 - end of packet
        host - id 10 - on bit
        moderator - id 20 - off bit
        contributor - id 25 - repeat previous bit
        """

        payload = "role="

        # Check if it's the same role as before
        if self.previous_role == bit_keys[bit]:
            # id 25 - contributor - repeat previous bit
            role_id = "25"
        else:
            # Not the same role as before
            role_id = bit_keys[bit]  

        payload += role_id
        self.previous_role = role_id

        # Send signal to user
        resp = await self.session.put(f"https://rooms.rec.net/rooms/{self.room_id}/roles/{self.account.id}", data=payload)
        return resp.status == 200