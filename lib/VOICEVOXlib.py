import aiohttp
import wave
import io
import os
from dotenv import load_dotenv
import time
import shutil
from prometheus_client import Gauge
import random
import logging  # 追加: エラーログ用

# Load environment variables
load_dotenv()

# Add a Prometheus gauge to record seconds of processing per 1 minute of generated audio
VOICE_GENERATION_TIME_PER_MINUTE = Gauge(
    'voice_generation_seconds_per_minute',
    '1分の音声生成にかかる平均処理時間（秒）'
)

class VOICEVOXLib:
    def __init__(self, base_url=None):
        self._base_url_arg = base_url  # 引数を保存
        self._default_url = "http://localhost:50021"
        # 初期化時は一度だけロード
        self.base_urls = self._load_base_urls()
        # プロジェクトルートの tmp ディレクトリを確保
        # lib ディレクトリの親をプロジェクトルートとみなし、その直下に tmp を作成する
        try:
            lib_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(lib_dir, ".."))
            self.tmp_dir = os.path.join(project_root, "tmp")
            os.makedirs(self.tmp_dir, exist_ok=True)
        except Exception:
            # 何らかの理由で作れない場合はカレントディレクトリの tmp を使う
            self.tmp_dir = os.path.join(os.getcwd(), "tmp")
            try:
                os.makedirs(self.tmp_dir, exist_ok=True)
            except Exception:
                # 最終手段として tmp_dir を None にしておく
                self.tmp_dir = None

    def _load_base_urls(self):
        # .envを毎回再読込
        load_dotenv(override=True)
        if self._base_url_arg is None:
            env_urls = os.getenv("VOICEVOX_URL", self._default_url)
            if not env_urls:
                env_urls = self._default_url
            return [u.strip() for u in env_urls.split(",") if u.strip()]
        else:
            if isinstance(self._base_url_arg, list):
                return self._base_url_arg
            else:
                return [self._base_url_arg]

    def _choose_base_url(self):
        # .envを毎回再読込してURLリストを更新
        self.base_urls = self._load_base_urls()
        return random.choice(self.base_urls)

    async def get_speakers(self):
        """Fetch available speakers from the VOICEVOX engine."""
        base_url = self._choose_base_url()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/speakers") as response:
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
        # .envを毎回再読込してURLリストを更新
        self.base_urls = self._load_base_urls()
        for base_url in self.base_urls:
            if os.getenv("DEBUG") == "1":
                print(f"Using VOICEVOX URL: {base_url}")
            last_error = None
            for attempt in range(3):
                try:
                    async with aiohttp.ClientSession() as session:
                        start_time = time.perf_counter()
                        # Step 1: Generate audio query
                        async with session.post(
                            f"{base_url}/audio_query",
                            params={"text": text, "speaker": speaker_id}
                        ) as query_response:
                            if query_response.status >= 500:
                                raise aiohttp.ClientResponseError(
                                    request_info=query_response.request_info,
                                    history=query_response.history,
                                    status=query_response.status,
                                    message=f"HTTP {query_response.status}",
                                    headers=query_response.headers
                                )
                            query_response.raise_for_status()
                            audio_query = await query_response.json()
                            if "speedScale" in audio_query:
                                audio_query["speedScale"] = speed

                        # Step 2: Synthesize audio
                        async with session.post(
                            f"{base_url}/synthesis",
                            params={"speaker": speaker_id},
                            json=audio_query
                        ) as synthesis_response:
                            if synthesis_response.status >= 500:
                                raise aiohttp.ClientResponseError(
                                    request_info=synthesis_response.request_info,
                                    history=synthesis_response.history,
                                    status=synthesis_response.status,
                                    message=f"HTTP {synthesis_response.status}",
                                    headers=synthesis_response.headers
                                )
                            synthesis_response.raise_for_status()
                            wav_bytes = await synthesis_response.read()

                        elapsed = time.perf_counter() - start_time

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

                            # 出力先をプロジェクトルートの tmp ディレクトリに固定し、そのパスを返す
                            filename = os.path.basename(output_path)
                            if self.tmp_dir:
                                tmp_output_path = os.path.join(self.tmp_dir, filename)
                            else:
                                tmp_output_path = os.path.abspath(output_path)

                            # tmp に保存
                            with wave.open(tmp_output_path, "wb") as output_file:
                                output_file.setparams(wav_file.getparams())
                                output_file.writeframes(wav_file.readframes(n_frames))

                            return tmp_output_path
                except aiohttp.ClientResponseError as e:
                    logging.error(f"VOICEVOX synthesis failed for URL {base_url} (attempt {attempt+1}/3): {e}")
                    last_error = e
                    time.sleep(0.5)
                    continue
                except aiohttp.ClientError as e:
                    logging.error(f"VOICEVOX synthesis failed for URL {base_url} (attempt {attempt+1}/3): {e}")
                    last_error = e
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    logging.error(f"VOICEVOX synthesis unexpected error for URL {base_url}: {e}")
                    break
            # 3回とも失敗した場合のみ次のURLへ
        raise RuntimeError(f"All VOICEVOX URLs failed for synthesis: {text[:50]}... Last error: {last_error}")

    async def synthesize_bytes(self, text, speaker_id) -> tuple[str, bytes]:
        """
        Synthesize speech from text and return audio data as bytes.

        Args:
            text (str): The text to synthesize.
            speaker_id (int): The ID of the speaker to use.

        Returns:
            tuple[str, bytes]: The used base URL and the synthesized speech audio data.
        """
        # .envを毎回再読込してURLリストを更新
        self.base_urls = self._load_base_urls()
        for base_url in self.base_urls:
            if os.getenv("DEBUG") == "1":
                print(f"Using VOICEVOX URL: {base_url}")
            last_error = None
            for attempt in range(3):
                try:
                    async with aiohttp.ClientSession() as session:
                        start_time = time.perf_counter()

                        # Step 1: Generate audio query
                        async with session.post(
                            f"{base_url}/audio_query",
                            params={"text": text, "speaker": speaker_id}
                        ) as query_response:
                            if query_response.status >= 500:
                                raise aiohttp.ClientResponseError(
                                    request_info=query_response.request_info,
                                    history=query_response.history,
                                    status=query_response.status,
                                    message=f"HTTP {query_response.status}",
                                    headers=query_response.headers
                                )
                            query_response.raise_for_status()
                            audio_query = await query_response.json()

                        # Step 2: Synthesize audio
                        async with session.post(
                            f"{base_url}/synthesis",
                            params={"speaker": speaker_id},
                            json=audio_query
                        ) as synthesis_response:
                            if synthesis_response.status >= 500:
                                raise aiohttp.ClientResponseError(
                                    request_info=synthesis_response.request_info,
                                    history=synthesis_response.history,
                                    status=synthesis_response.status,
                                    message=f"HTTP {synthesis_response.status}",
                                    headers=synthesis_response.headers
                                )
                            synthesis_response.raise_for_status()
                            wav_bytes = await synthesis_response.read()

                        elapsed = time.perf_counter() - start_time

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

                        return base_url, wav_bytes
                except aiohttp.ClientResponseError as e:
                    logging.error(f"VOICEVOX synthesize_bytes failed for URL {base_url} (attempt {attempt+1}/3): {e}")
                    last_error = e
                    time.sleep(0.5)
                    continue
                except aiohttp.ClientError as e:
                    logging.error(f"VOICEVOX synthesize_bytes failed for URL {base_url} (attempt {attempt+1}/3): {e}")
                    last_error = e
                    time.sleep(0.5)
                    continue
                except Exception as e:
                    logging.error(f"VOICEVOX synthesize_bytes unexpected error for URL {base_url}: {e}")
                    break
            # 3回とも失敗した場合のみ次のURLへ
        raise RuntimeError(f"All VOICEVOX URLs failed for synthesize_bytes: {text[:50]}... Last error: {last_error}")

# Example usage:
# voicelib = VOICEVOXLib()
# speakers = voicelib.get_speakers()
# print(speakers)
# voicelib.synthesize("こんにちは、世界！", speaker_id=1, output_path="output.wav")
