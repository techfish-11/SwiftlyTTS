import aiohttp
import wave
import io
import asyncio

class VOICEVOXLib:
    def __init__(self, base_url="http://192.168.1.107:50021"):
        self.base_url = base_url

    async def get_speakers(self):
        """Fetch available speakers from the VOICEVOX engine."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/speakers") as response:
                response.raise_for_status()
                return await response.json()

    async def synthesize(self, text, speaker_id, output_path):
        """
        Synthesize speech from text using the VOICEVOX engine.

        Args:
            text (str): The text to synthesize.
            speaker_id (int): The ID of the speaker to use.
            output_path (str): Path to save the output WAV file.
        """
        async with aiohttp.ClientSession() as session:
            # Step 1: Generate audio query
            async with session.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": speaker_id}
            ) as query_response:
                query_response.raise_for_status()
                audio_query = await query_response.json()

            # Step 2: Synthesize audio
            async with session.post(
                f"{self.base_url}/synthesis",
                params={"speaker": speaker_id},
                json=audio_query
            ) as synthesis_response:
                synthesis_response.raise_for_status()
                wav_bytes = await synthesis_response.read()

            # Step 3: Save WAV file
            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                with wave.open(output_path, "wb") as output_file:
                    output_file.setparams(wav_file.getparams())
                    output_file.writeframes(wav_file.readframes(wav_file.getnframes()))

    async def synthesize_bytes(self, text, speaker_id) -> bytes:
        """
        Synthesize speech from text and return audio data as bytes.

        Args:
            text (str): The text to synthesize.
            speaker_id (int): The ID of the speaker to use.

        Returns:
            bytes: The synthesized speech audio data.
        """
        async with aiohttp.ClientSession() as session:
            # Step 1: Generate audio query
            async with session.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": speaker_id}
            ) as query_response:
                query_response.raise_for_status()
                audio_query = await query_response.json()

            # Step 2: Synthesize audio
            async with session.post(
                f"{self.base_url}/synthesis",
                params={"speaker": speaker_id},
                json=audio_query
            ) as synthesis_response:
                synthesis_response.raise_for_status()
                wav_bytes = await synthesis_response.read()

            return wav_bytes

# Example usage:
# voicelib = VOICEVOXLib()
# speakers = voicelib.get_speakers()
# print(speakers)
# voicelib.synthesize("こんにちは、世界！", speaker_id=1, output_path="output.wav")