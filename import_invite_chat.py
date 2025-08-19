import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.errors import InviteHashExpiredError, InviteHashInvalidError, UserAlreadyParticipantError

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

async def import_chat_invite(invite_link: str):
    """
    Import a private Telegram chat via its invite link.
    Prints the resulting Updates object or any error.
    """
    # Extract the invite hash (supports both t.me/joinchat/XYZ and t.me/+XYZ)
    invite_hash = invite_link.split('+')[-1]
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    
    # Check if already a member
    invite_status = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
    if isinstance(invite_status, types.ChatInviteAlready):
        print("Already a member of this chat")
        await client.disconnect()
        return

    try:
        result = await client(functions.messages.ImportChatInviteRequest(hash=invite_hash))
        print("Import successful:", result)
    except InviteHashExpiredError:
        print("Failed to import invite link: Invite link has expired")
    except InviteHashInvalidError:
        print("Failed to import invite link: Invalid invite link")
    except UserAlreadyParticipantError:
        print("Already a member of this chat")
    except Exception as e:
        print("Failed to import invite link:", e)
    finally:
        await client.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_invite_chat.py <invite_link>")
        sys.exit(1)

    link = sys.argv[1]
    asyncio.run(import_chat_invite(link))
