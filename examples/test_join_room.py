import asyncio
import os
from dotenv import load_dotenv
from livekit import api
from livekit.agents import JobContext, WorkerOptions, cli

load_dotenv()

async def join_room_entrypoint(ctx: JobContext):
    """Join room and log connection details"""
    try:
        print(f"\n✓ Successfully connected!")
        print(f"  Room: {ctx.room.name}")
        print(f"  Participants: {len(ctx.room.participants)}")
        print(f"  Your ID: {ctx.room.local_participant.identity}")
        
        # Keep connection alive
        await asyncio.sleep(30)
        print("✓ Connection test completed!")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=join_room_entrypoint))