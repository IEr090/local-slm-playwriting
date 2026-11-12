import pickle
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import ChannelVersions, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.base import SerializerProtocol


class FileCheckpointer(InMemorySaver):
    """Keep the conversations in memory like InMemorySaver and write them to a file after every change.

    The file holds the already serialized checkpoints, so a restarted backend continues every chat.
    """

    def __init__(self, path: Path, serde: SerializerProtocol | None = None) -> None:
        """Initialize the store and read the conversations saved in the file, if there is one."""
        super().__init__(serde=serde)
        self.path = path
        if path.exists():
            saved = pickle.loads(path.read_bytes())
            for thread_id, namespaces in saved["storage"].items():
                for checkpoint_ns, checkpoints in namespaces.items():
                    self.storage[thread_id][checkpoint_ns].update(checkpoints)
            self.writes.update(saved["writes"])
            self.blobs.update(saved["blobs"])

    def put(
        self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Save the checkpoint and write the store to the file."""
        result = super().put(config, checkpoint, metadata, new_versions)
        self._save()
        return result

    def put_writes(self, config: RunnableConfig, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        """Save the pending writes and write the store to the file."""
        super().put_writes(config, writes, task_id, task_path)
        self._save()

    def delete_thread(self, thread_id: str) -> None:
        """Forget the conversation and write the store to the file."""
        super().delete_thread(thread_id)
        self._save()

    def _save(self) -> None:
        """Write the store to a temporary file first so a crash never leaves a broken file."""
        storage = {}
        for thread_id, namespaces in self.storage.items():
            storage[thread_id] = {}
            for namespace, items in namespaces.items():
                storage[thread_id][namespace] = dict(items)

        data = {
            "storage": storage,
            "writes": {key: dict(value) for key, value in self.writes.items()},
            "blobs": dict(self.blobs),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(pickle.dumps(data))
        temporary.replace(self.path)


__all__ = ["FileCheckpointer"]
