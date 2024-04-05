"""
This example sends "Hello, World!" to the specified recipient.
This example also instructs you on the initialization process.

In-game 'Receiver' circuit board must be connected to 'Packet Handler'.
In order to decode the text, you must use the 'Decimal to Character' circuit board.

The text is sent in decimals unique to this library. We don't use character encoding standards like ASCII or UTF-8.
Some characters are not yet supported. 'supported_characters()' function from the library helpers returns all supported characters.
"""

import asyncio
import circuitsapi
from dotenv import dotenv_values

async def main():
    """
    Let's first login to our host account. This account must be an owner OR co-owner
    in the room we want to send data to.

    CircuitsAPI has RecNetLogin integrated. If you want to use any other method of fetching the token,
    you may do so and pass it to the client as the 'rr_auth' argument.

    Read https://github.com/Jegarde/RecNet-Login to understand how to setup RecNetLogin.
    """
    print("\n1. Logging in to RecNet")
    access_token = None

    """
    Make sure you have a developer token from https://devportal.rec.net/.
    Include the token in a '.env.secret' file with the key 'DEV_API_TOKEN'.
    Ex. 'DEV_API_TOKEN=cOEUXZgVIZs6pxS...'
    """
    print("\n2. Fetching developer API token")
    env = dotenv_values(".env.secret")
    dev_api_token = env.get("DEV_API_TOKEN")
    if not dev_api_token:
        print("Unable to find your developer API token!")
        return

    # Let's initialize the CircuitsAPI client!
    print("\n3. Initializing CircuitsAPI")
    async with circuitsapi.Client(dev_token=dev_api_token, rr_auth=access_token) as client:
        """
        Now that we have initialized the CircuitsAPI client, we can now connect to a room.
        This room must be owned or co-owned by the account we just logged in as.
        This room must also have the 'Receiver' circuit board.
        """
        print("\n4. Connecting to a room")
        room = await client.connect_to_room(room=input("Enter room ID or name > "))

        """
        Now that we have connected to our room, let's connect to a user. This user
        will receive the data.
        The user must be in the room. They cannot be an owner nor a co-owner.
        """
        print("\n5. Connecting to an user")
        user = await room.connect_to_user(user=input("Enter account ID or username > "))

        """
        We have now successfully connected to our recipient!
        We can now start sending data.
        """
        print("\n6. Sending 'Hello, World!' to user")
        await user.send_text_packet("Hello, World!")

        # Finished!
        print("\n7. Done! Farewell, World...")


asyncio.run(main())
