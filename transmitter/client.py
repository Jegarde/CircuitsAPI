import asyncio
import aiohttp
import recnetpy
import time
import jwt
from aiohttp.client_exceptions import ServerDisconnectedError
from typing import Optional, List
from dataclasses import dataclass
from recnetpy.dataclasses.account import Account
from .helpers import *
from .exceptions import *
from .request import Request


@dataclass
class LoginCookie:
    csrf_token: str
    session_token: str

class Client:
    def __init__(self, dev_token: str, rr_token: LoginCookie, debug_mode: bool = False):
        # Dev token
        self.dev_token = dev_token

        # Headers & cookies
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        self.cookies = {}
        self.access_token = None
        self.access_to_matchmaking = False

        # host account ID
        self.host_account_id = 0

        # Determine login method
        if isinstance(rr_token, LoginCookie):
            # Cookie login method
            self.cookies = {"__Host-next-auth.csrf-token": rr_token.csrf_token, "__Secure-next-auth.session-token": rr_token.session_token}
            self.cookie_method = True
        else:
            self.headers["Authorization"] = "Bearer " + rr_token
            self.access_token = rr_token
            self.cookie_method = False

        # clients
        self.session: aiohttp.ClientSession | None = None
        self.RecNet: recnetpy.Client | None = None

        # debug mode for printing
        self.debug = debug_mode

        # Initialized
        self.initialized = False

    async def initialize(self):
        if self.initialized: return
        
        self.session = aiohttp.ClientSession(headers=self.headers, cookies=self.cookies)
        self.RecNet = recnetpy.Client(api_key=self.dev_token)

        # Check if logged in with cookie
        if self.cookie_method:
            # Get access token
            resp = await self.send_request("get", "https://rec.net/api/auth/session")
            data = await resp.json()
            token = data.get("accessToken")
            assert token, "Couldn't login!"
            self.access_token = token
            self.session.headers["Authorization"] = "Bearer " + token

        decoded_token = self.__decode_token(self.access_token)
        self.host_account_id = int(decoded_token.get("sub", "0"))
        self.access_to_matchmaking = "rn.match.read" in decoded_token.get("scope", [])

        if not self.access_to_matchmaking:
            print("WARNING: Your access token is lacking the 'rn.match.read' scope. This will limit functionality.")

        self.initialized = True

    async def send_request(self, method: str, url: str, payload: str | dict = {}):
        request = Request(self.session, method, url, payload)
        return await request.send_request()

    async def connect_to_room(self, room: str | int):
        conn: RoomConnection = RoomConnection(room, self)
        await conn.initialize()
        return conn
    
    def __decode_token(self, token: str) -> dict:
        """Decodes a bearer token

        Args:
            token (str): A bearer token

        Returns:
            dict: Decoded bearer token
        """
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded

    async def db_print(self, *args) -> None:
        if self.debug: print("Transmitter -", args)

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
        resp = await self.client.send_request("get", f"https://rooms.rec.net/rooms/{self.room_id}/roles/")
        roles = await resp.json()
        if roles == []: raise RoomNotFound

        # Make sure the user is privileged in the room so data can be transmitted
        is_privileged = False
        for i in roles:
            if i["AccountId"] == self.client.host_account_id and i["Role"] in (255, 30):
                is_privileged = True
                break
        
        # Check if privileges found!
        if not is_privileged:
            raise InvalidRoomConnection

        self.roles = await resp.json()
        

    async def connect_to_user(self, user: str | int):
        """Creates a connection to the specified user.

        Args:
            user (str | int): Username or ID

        Raises:
            UserNotFound: Raised if the user doesn't exist.
            UserNotInRoom: Raised if the user is not in the room.

        Returns:
            UserConnection: Connection to the user.
        """
        # Find user
        if isinstance(user, int):
            account = await self.RecNet.accounts.fetch(user)
        else:
            account = await self.RecNet.accounts.get(user)
        if not account: raise UserNotFound

        conn = UserConnection(account=account, room_connection=self)

        if self.client.access_to_matchmaking:
            # Check if the player is in the room
            if await conn.check_is_player_in_room():
                return conn
            else:
                raise UserNotInRoom
        else:
            # Can't check if the player is in the room
            return conn
            

    async def find_players(self) -> Optional[List[int]]:
        """Searches for players in the room using room images taken in the past 10 minutes.

        Returns:
            Optional[List[int]]: List of found players' IDs.
        """
        # Finds players in the room from images
        resp = await self.client.send_request("get", f"https://apim.rec.net/apis/api/images/v4/room/{self.room_id}?take=10")
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
        self.client = self.room_conn.client

        # Room ID
        self.room_id = self.room_conn.room_id

        # Connected account
        self.account = account

        # aiohttp session
        self.session = self.room_conn.session

        # previous role
        self.previous_role: int = self.__get_current_role()

        # Check if the user is an owner or co-owner or the account transmitting data
        if self.previous_role in ("255", "30"):
            raise ConnectingToPrivilegedUser

        # available characters
        self.characters = supported_characters()

        # is transmitting packets?
        self.transmitting_packets = False
        self.latest_bit_timestamp = 0  # For detecting timeouts


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
        await self.__transmit_packet(0)

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


    async def check_is_player_in_room(self) -> bool:
        """Returns True if connected player is in the connected room.

        Returns:
            bool: True if player is in the room
        """
        instance = await self.get_instance()
        return instance and instance.get("roomId") == self.room_id


    async def get_instance(self) -> dict | None:
        """Returns the instance connected players is in.

        Returns:
            dict | None: Instance data if successful
        """

        # Check if the client can access matchmaking data
        if not self.client.access_to_matchmaking:
            raise LackingScope('rn.match.read')

        resp = await self.client.send_request("get", f"https://match.rec.net/player?id={self.account.id}")
        if resp.status != 200: return None
        
        # Get user's current instance
        data = await resp.json()
        instance = data[0].get("roomInstance")
        if not instance: return None

        return instance
    

    # Backend functions

    def __get_current_role(self) -> str:
        """Returns the current role of the connected account

        Returns:
            str: Role ID as string
        """
        for i in self.room_conn.roles:
            if i["AccountId"] == self.account.id:
                return str(i["Role"])
        return "0"
    

    async def __transmit_packet(self, binary: int):
        """Transmits a packet to the 'Packet Handler' circuit board. 

        Args:
            binary (int): Binary number to transmit
        """
        bits = [*str(binary)]
        bits.reverse()
        for bit in bits:
            await self.__transmit_bit(int(bit))
        await self.__packet_completed()


    async def __transmit_packet_count(self, content_length: int):
        """Signals the amount of packets in the payload to the 'Packet Handler' circuit board.
        """

        self.transmitting_packets = True
        await self.__transmit_packet(int(f"{content_length:b}"))


    async def __packet_completed(self) -> bool:
        """Signals to the 'Packet Handler' circuit board that a packet was fully sent.

        Returns:
            bool: Was it successful?
        """
        self.transmitting_packets = False
        self.latest_bit_timestamp = 0
        payload = "role="

        # Check if it's the same bit as before
        if self.previous_role == "0":
            role_id = "25"
        else:
            role_id = "0"

        payload += role_id
        self.previous_role = role_id

        resp = await self.client.send_request("put", f"https://rooms.rec.net/rooms/{self.room_id}/roles/{self.account.id}", payload=payload)
        return resp.status == 200


    async def __transmit_bit(self, bit: int) -> bool:
        """Transmits a bit to the 'Receiver' circuit board

        Args:
            bit (int): Bit to transmit

        Returns:
            bool: Was it successful?
        """

        # Check if a possible payload was timed out
        if self.transmitting_packets and self.latest_bit_timestamp != 0:
            # Has it been over 10 seconds since the last bit was sent?
            if self.latest_bit_timestamp - time.time() >= 10:
                self.transmitting_packets = False
                self.latest_bit_timestamp = 0
                raise TimedOut

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
        resp = await self.client.send_request("put", f"https://rooms.rec.net/rooms/{self.room_id}/roles/{self.account.id}", payload)

        # Save the timestamp this bit was sent.
        # If the next bit takes over 10 seconds to send, the payload has timed out in-game.
        if self.transmitting_packets:
            self.latest_bit_timestamp = time.time()

        return resp.status == 200
    

    