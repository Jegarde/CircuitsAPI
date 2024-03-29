class RoomNotFound(Exception):
    def __init__(self):            
        super().__init__("Room not found! If the room is private, make sure the host account is a co-owner.")

    
class UserNotFound(Exception):
    def __init__(self):            
        super().__init__("User not found!")