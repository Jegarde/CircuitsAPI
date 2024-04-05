![promo image](https://i.imgur.com/sk1KyTT.png)

## THIS PROJECT IS IN PRE-ALPHA STAGE
This system has not been properly tested. It is constantly being updated with breaking changes. Do not use this system in a production environment. Only use it for testing and experimenting.

## What is this?
A system to communicate with CV2 using Python.


## Limitations
You must sacrifice the following permission roles: host, moderator & contributor. Co-owner will be the only role you can grant others without triggering the system. 

Room owner & co-owners will not be able to receive data by this system.

You can only send a single bit at once. This system is not applicable for big data transmissions.

CV2 pongs require messing with the instance's matchmaking state.

The circuits are currently made in Rooms v2. I am working on porting the circuits to Rooms v1 so it can be saved as an invention.


## Setup
1. Clone the template room: https://rec.net/room/CircuitsAPI.
2. **IMPORTANT:** Remove any privileged permissions from the following roles from the room: host, moderator & contributor. Otherwise you may risk troublemakers abusing the privileges.
3. Add `circuitsapi` as a room tag to indicate it's supported.
4. Activate the 'Receiver' circuit board.


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
