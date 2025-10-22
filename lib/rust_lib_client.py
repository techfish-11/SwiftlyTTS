import rust_queue

class RustQueueClient:
    def add(self, guild_id: int, text: str, speaker_id: int) -> None:
        print(f"Adding to Rust queue")
        rust_queue.add_to_queue(guild_id, text, speaker_id)

    def get_next(self, guild_id: int):
        result = rust_queue.get_next(guild_id)
        if result is not None:
            text, speaker_id = result
            return text, speaker_id
        return None

    def clear(self, guild_id: int) -> None:
        print(f"Clearing Rust queue")
        rust_queue.clear_queue(guild_id)

    def length(self, guild_id: int) -> int:
        print(f"Getting length of Rust queue")
        return rust_queue.queue_length(guild_id)
