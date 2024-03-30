class RoomNotFound(Exception):
    def __init__(self):            
        super().__init__("Room not found! If the room is private, make sure the host account is a co-owner.")

class UserNotFound(Exception):
    def __init__(self):            
        super().__init__("User not found!")

class UserNotInRoom(Exception):
    def __init__(self):            
        super().__init__("User is not in the connected room!")

class TimedOut(Exception):
    """Raised when the payload being transmitted was timed out by the 'Packet Handler' circuit board."""
    def __init__(self) -> None:
        super().__init__("The payload was timed out in-game. Try sending it again.")

class ConnectingToPrivilegedUser(Exception):
    """Raised when trying to connect to the account transmitting data, co-owners or the owner."""
    def __init__(self) -> None:
        super().__init__("Cannot connect to an account that is the owner of the room or a co-owner.")

class InvalidRoomConnection(Exception):
    """Raised when trying to connect to a room where the host account doesn't have privileges in."""
    def __init__(self) -> None:
        super().__init__("Cannot connect to a room where the host account doesn't have co-owner or owner.")

class LackingScope(Exception):
    """Raised when trying to fetch data without the necessary scope in access token."""
    def __init__(self, scope: str) -> None:
        super().__init__(f"Cannot fetch data because your access token lacks the {scope} scope.")