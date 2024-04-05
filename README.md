![promo](https://github.com/Jegarde/CircuitsAPI/assets/13438202/554a02af-6862-44d9-aa80-da78fccdb409)

## THIS PROJECT IS IN PRE-ALPHA STAGE
This system has not been properly tested. It is constantly being updated with breaking changes. Do not use this system in a production environment. Only use it for testing and experimenting.

Detailed documentation coming later.

## What is this?
A system to communicate with CV2 using Python.

<img src="https://github.com/Jegarde/CircuitsAPI/assets/13438202/fad38801-641f-439f-ab36-249bc22d08e9" width="400">
<img src="https://github.com/Jegarde/CircuitsAPI/assets/13438202/70d09f93-8f40-4dff-8c26-f1577d91ba6f" width="350">



## Limitations
- You must sacrifice the following permission roles: host, moderator & contributor. Co-owner will be the only role you can grant others without triggering the system. 
- Room owner & co-owners will not be able to receive data by this system.
- You can only send a single bit at once. This system is not applicable for big data transmissions.
- CV2 pongs require messing with the instance's matchmaking state.
- The circuits are currently made in Rooms v2 to prevent the system being used in existing production rooms due to instability.
  - It will be ported over to Rooms v1 once it's stable enough.

## Installation
The recommended method is installing via [pip](https://pypi.org/project/pip/).

`pip install -U circuitsapi`

For instructions on installing Python and pip, see [The Hitchhiker's Guide to Python](https://docs.python-guide.org/starting/installation/).

## Setup
Clone the template room: https://rec.net/room/CircuitsAPI.

Request a developer key from https://devportal.rec.net/. This will be passed as the `dev_token` argument in the client.

Setup RecNetLogin: https://github.com/Jegarde/RecNet-Login/?tab=readme-ov-file#setup.

## Quickstart
Here's the basics of setting up the client: 
```py
import circuitsapi
import asyncio

async def main():
    # Let's initialize the CircuitsAPI client!
    # dev_token is the developer key from https://devportal.rec.net/.
    # rr_auth is the RecNet access token. If left empty, CircuitsAPI defaults to RecNetLogin: https://github.com/Jegarde/RecNet-Login/
    async with circuitsapi.Client(dev_token="", rr_auth=None) as client:
        # Connect to a supported room
        room = await client.connect_to_room(room="CircuitsAPI")  # You can also use the room ID
    
        # Connect to a specific user to send data to
        user = await room.connect_to_user(user="Jegarde")  # You can also use the account ID
    
        # Send signals to the receiver ports
        await user.send_bit_1()
        await user.send_bit_0()
        await user.send_end_signal()

        # Send binary
        await user.send_binary(101101)

asyncio.run(main())
```

<img src="https://github.com/Jegarde/CircuitsAPI/assets/13438202/6ed9b3b4-a14f-4ef2-8a8b-79d76fa0e29f" height="300">

Here's the functions you can use if you hook up the in-game 'Receiver' to the 'Packet Handler':
```py
# Assuming you are connected to an user

# Sending text
await user.send_text_packet("Hello, World!")

# Sending integers
await user.send_int_packet(69420)

# Ping the in-game Packet Handler
await user.ping()
```

Here's some miscellaneous functions:
```py
# Returns true if the player is in the specified room
# Requires 'rn.match.read' scope in access token.
await user.check_is_player_in_room()

# Returns the player's room instance data
# Requires 'rn.match.read' scope in access token.
await user.get_instance()

# Returns player IDs of those who have taken images in the past 10 minutes
# If you want to connect to users, you can ask them to take pictures and have the server check for those pictures
await room.find_players()
```

## How does this work?
There's CV2 chips for checking if a player is a host, mod or a contributor and you can modify a player's roles through the API. This allows us to send remote signals to the specified player while CV2 is constantly checking for each players' roles.

RR Transmitter uses the following signals:
```
Host = Add on bit
Mod = Add off bit
Contributor = Repeat previous bit
No role = End of binary number
```

So if we wanted to transmit 1011 in binary numbers, the following signals would be sent:

```py
>>> Modify [player] role to Host # Add on bit
>>> Modify [player] role to Mod  # Add off bit
>>> Modify [player] role to Host # Add on bit
>>> Modify [player] role to Contributor # Add on bit (repeat previous bit)
>>> Modify [player] role to None # End of binary number
```

### Modify role request
```
POST /rooms/{ROOM_ID}/roles/{PLAYER_ID} HTTP/1.1
Host: rooms.rec.net
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/x-www-form-urlencoded

role={0 | 10 | 20 | 25}
```

Requires an access token from an account with owner / co-owner in the specified room.

Role | ID
--- | ---
None | 0
Host | 10
Mod | 20
Contributor | 25
Co-owner | 30
