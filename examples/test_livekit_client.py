import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import api
from livekit.agents import JobContext, WorkerOptions, cli

# Load environment variables from .env
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("livekit-test-client")

async def test_entrypoint(ctx: JobContext):
    """Test script to verify LiveKit room connection"""
    try:
        logger.info(f"✓ Connected to room: {ctx.room.name}")
        logger.info(f"✓ Room metadata: {ctx.room.metadata}")
        logger.info(f"✓ Participants: {len(ctx.room.participants)}")
        logger.info("✓ LiveKit connection successful!")
    except Exception as e:
        logger.error(f"✗ Connection failed: {str(e)}")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=test_entrypoint))