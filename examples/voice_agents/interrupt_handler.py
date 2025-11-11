import asyncio
import logging
from livekit.agents import AgentSession, UserInputTranscribedEvent

class AsyncSafeInterruptHandler:
    """
    This class implements the transcription-driven interruption logic.
    
    It is "async-safe" because the livekit-agents SDK uses asyncio,
    not traditional OS threads.[4] We use an asyncio.Lock to protect
    our internal state (_is_agent_speaking) from concurrent access
    by different event callbacks (like 'on_transcribed' and 
    'on_agent_stopped_speaking' firing close together).[5, 6]
    """

    def __init__(self, ignored_words: set[str]):
        self._ignored_words = ignored_words
        self._is_agent_speaking = False
        self._lock = asyncio.Lock()  # Lock to protect shared state [5]
        self._session: AgentSession | None = None

    def attach(self, session: AgentSession):
        """
        Attaches the handler to the AgentSession's event loop
        by subscribing to the required events.
        """
        self._session = session
        
        # Listen for agent speech state changes [7, 8]
        session.on("agent_started_speaking", self.on_agent_started_speaking)
        session.on("agent_stopped_speaking", self.on_agent_stopped_speaking)
        
        # Listen for user transcription events [9]
        session.on("user_input_transcribed", self.on_user_input_transcribed)

    async def on_agent_started_speaking(self):
        """Async-safe callback for when the agent starts speaking."""
        async with self._lock:
            self._is_agent_speaking = True
            logging.debug("InterruptHandler: Agent started speaking.")

    async def on_agent_stopped_speaking(self):
        """Async-safe callback for when the agent stops speaking."""
        async with self._lock:
            self._is_agent_speaking = False
            logging.debug("InterruptHandler: Agent stopped speaking.")

    async def on_user_input_transcribed(self, event: UserInputTranscribedEvent):
        """
        This is the core logic. It analyzes transcripts to decide
        whether to manually interrupt the agent.
        """
        if not self._session:
            return

        # Use the lock to ensure state is consistent during this check [10]
        async with self._lock:
            # Scenarios 4 & 5: Agent is quiet.
            # We do nothing and let LiveKit process the turn normally.
            if not self._is_agent_speaking:
                logging.debug(
                    f"InterruptHandler: Ignoring transcript, agent quiet: {event.transcript}"
                )
                return

            # Scenarios 1, 2, 3: Agent is speaking.
            # We must analyze the transcript.
            is_genuine = self._is_genuine_interruption(event.transcript)

            if is_genuine:
                # Scenario 2 & 3: Genuine interruption ("stop", "umm okay stop").
                # Manually interrupt the session.[11]
                logging.info(
                    f"Genuine interruption detected, stopping agent: {event.transcript}"
                )
                await self._session.interrupt()
            else:
                # Scenario 1: Filler-only interruption ("uh", "umm").
                # We do nothing, which allows the agent to continue speaking.
                logging.info(f"Ignoring filler interruption: {event.transcript}")

    def _is_genuine_interruption(self, transcript: str) -> bool:
        """
        Checks if a transcript contains any non-filler words.
        This is designed to handle interim results (is_final=False).[9]
        """
        normalized = transcript.lower().strip()
        if not normalized:
            return False  # Empty transcript

        words = normalized.split()

        for word in words:
            # Simple cleaning for comparison
            cleaned_word = word.strip(".,?!")
            if cleaned_word and cleaned_word not in self._ignored_words:
                # Found a word that is NOT a filler.
                # This is a genuine interruption.
                return True

        # All words in the transcript were in the ignored list.