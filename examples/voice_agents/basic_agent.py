import logging
import os
import asyncio
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
)

from livekit.plugins import (
    openai,
    silero
)

from livekit.agents.llm import function_tool
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Import the interrupt handler
from interrupt_handler import AsyncSafeInterruptHandler

logger = logging.getLogger("basic-agent")

load_dotenv()

# Load and parse the configurable ignored words from environment 
IGNORED_WORDS_STR = os.environ.get("IGNORED_WORDS", "uh,umm,hmm,haan")
IGNORED_WORDS_SET = set(IGNORED_WORDS_STR.split(','))


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice. "
            "With that in mind keep your responses concise and to the point. "
            "Do not use emojis, asterisks, markdown, or other special characters in your responses. "
            "You are curious and friendly, and have a sense of humor. "
            "You will speak english to the user.",
        )

    async def on_enter(self):
        self.session.generate_reply()

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logging.info(f"Using ignored words: {IGNORED_WORDS_SET}")
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    agent = MyAgent()

    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4-mini",
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        false_interruption_timeout=1.0,
        allow_interruptions=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
