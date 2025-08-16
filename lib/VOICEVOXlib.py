import aiohttp
import wave
import io
import asyncio
import os
from dotenv import load_dotenv
import time
from prometheus_client import Gauge

# Load environment variables
load_dotenv()

# Add a Prometheus gauge to record seconds of processing per 1 minute of generated audio
VOICE_GENERATION_TIME_PER_MINUTE = Gauge(
    'voice_generation_seconds_per_minute',
    '1分の音声生成にかかる平均処理時間（秒）'
)

class VOICEVOXLib:
    def __init__(self, base_url=None):
        if base_url is None:
            base_url = os.getenv("VOICEVOX_URL", "http://192.168.1.11:50021")
            # Handle empty string case - use default if empty
            if not base_url:
                base_url = "http://192.168.1.11:50021"
        self.base_url = base_url

    async def get_speakers(self):
        """Fetch available speakers from the VOICEVOX engine."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/speakers") as response:
                response.raise_for_status()
                return await response.json()

    async def synthesize(self, text, speaker_id, output_path, speed: float = 1.0):
        """
        Synthesize speech from text using the VOICEVOX engine.

        Args:
            text (str): The text to synthesize.
            speaker_id (int): The ID of the speaker to use.
            output_path (str): Path to save the output WAV file.
            speed (float): Speed of the synthesized voice (default 1.0).
        """
        async with aiohttp.ClientSession() as session:
            start_time = time.perf_counter()  # 計測開始

            # Step 1: Generate audio query
            async with session.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": speaker_id}
            ) as query_response:
                query_response.raise_for_status()
                audio_query = await query_response.json()
                # スピードを上書き
                if "speedScale" in audio_query:
                    audio_query["speedScale"] = speed

            # Step 2: Synthesize audio
            async with session.post(
                f"{self.base_url}/synthesis",
                params={"speaker": speaker_id},
                json=audio_query
            ) as synthesis_response:
                synthesis_response.raise_for_status()
                wav_bytes = await synthesis_response.read()

            elapsed = time.perf_counter() - start_time  # 秒

            # Step 3: Save WAV file and compute duration
            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                n_frames = wav_file.getnframes()
                framerate = wav_file.getframerate()
                duration_sec = n_frames / framerate if framerate else 0.0

                # Update Prometheus metric: seconds of processing per 1 minute of audio
                if duration_sec > 0:
                    seconds_per_minute = elapsed * 60.0 / duration_sec
                else:
                    seconds_per_minute = 0.0
                try:
                    VOICE_GENERATION_TIME_PER_MINUTE.set(seconds_per_minute)
                except Exception:
                    # 安全のため例外は無視（メトリクス失敗で処理を止めない）
                    pass

                with wave.open(output_path, "wb") as output_file:
                    output_file.setparams(wav_file.getparams())
                    output_file.writeframes(wav_file.readframes(n_frames))

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
            start_time = time.perf_counter()  # 計測開始

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

            elapsed = time.perf_counter() - start_time  # 秒

            # Compute duration and set metric
            try:
                with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                    n_frames = wav_file.getnframes()
                    framerate = wav_file.getframerate()
                    duration_sec = n_frames / framerate if framerate else 0.0
                    if duration_sec > 0:
                        seconds_per_minute = elapsed * 60.0 / duration_sec
                    else:
                        seconds_per_minute = 0.0
                    VOICE_GENERATION_TIME_PER_MINUTE.set(seconds_per_minute)
            except Exception:
                # 例外は無視して wav_bytes を返す（メトリクスの失敗で処理を止めない）
                pass

            return wav_bytes

# Example usage:
# voicelib = VOICEVOXLib()
# speakers = voicelib.get_speakers()
# print(speakers)
# voicelib.synthesize("こんにちは、世界！", speaker_id=1, output_path="output.wav")
