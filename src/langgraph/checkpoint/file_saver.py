from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import threading
from collections.abc import AsyncIterator, Iterator, Sequence
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)


class FileSaver(BaseCheckpointSaver[str]):
    """
    Checkpointer LangGraph persistant utilisant un fichier JSON
    par thread et namespace.

    Cette implémentation convient à un seul processus Python.
    """

    def __init__(self, directory: str | Path = "var/checkpoints") -> None:
        super().__init__()

        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

        self._sync_lock = threading.RLock()
        self._async_locks: dict[str, asyncio.Lock] = {}
        self._async_locks_guard = threading.Lock()

    # ------------------------------------------------------------------
    # Helpers de configuration
    # ------------------------------------------------------------------

    @staticmethod
    def _get_thread_id(config: RunnableConfig) -> str:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")

        if thread_id is None:
            raise ValueError(
                "FileSaver requires "
                "config['configurable']['thread_id']"
            )

        return str(thread_id)

    @staticmethod
    def _get_checkpoint_namespace(config: RunnableConfig) -> str:
        configurable = config.get("configurable", {})
        return str(configurable.get("checkpoint_ns", ""))

    @staticmethod
    def _get_checkpoint_id(config: RunnableConfig) -> str | None:
        configurable = config.get("configurable", {})
        checkpoint_id = configurable.get("checkpoint_id")

        if checkpoint_id is None:
            return None

        return str(checkpoint_id)

    @staticmethod
    def _safe_filename(value: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)

        if not safe:
            return "default"

        return safe[:180]

    def _path_from_values(
        self,
        thread_id: str,
        checkpoint_ns: str,
    ) -> Path:
        thread_part = self._safe_filename(thread_id)
        namespace_part = self._safe_filename(
            checkpoint_ns or "default"
        )

        return self.directory / (
            f"{thread_part}__{namespace_part}.json"
        )

    def _path(self, config: RunnableConfig) -> Path:
        return self._path_from_values(
            thread_id=self._get_thread_id(config),
            checkpoint_ns=self._get_checkpoint_namespace(config),
        )

    def _get_async_lock(self, path: Path) -> asyncio.Lock:
        key = str(path)

        with self._async_locks_guard:
            lock = self._async_locks.get(key)

            if lock is None:
                lock = asyncio.Lock()
                self._async_locks[key] = lock

            return lock

    # ------------------------------------------------------------------
    # Sérialisation LangGraph
    # ------------------------------------------------------------------

    def _serialize(self, value: Any) -> dict[str, str]:
        value_type, data = self.serde.dumps_typed(value)

        return {
            "type": value_type,
            "data": base64.b64encode(data).decode("ascii"),
        }

    def _deserialize(self, value: dict[str, str]) -> Any:
        return self.serde.loads_typed(
            (
                value["type"],
                base64.b64decode(value["data"]),
            )
        )

    # ------------------------------------------------------------------
    # Lecture / écriture disque
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_storage() -> dict[str, Any]:
        return {
            "checkpoints": {},
            "writes": {},
        }

    def _read_storage(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return self._empty_storage()

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Invalid checkpoint file: {path}"
            ) from error

        data.setdefault("checkpoints", {})
        data.setdefault("writes", {})

        return data

    def _write_storage(
        self,
        path: Path,
        storage: dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = path.with_suffix(
            path.suffix + ".tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                storage,
                file,
                ensure_ascii=False,
                indent=2,
            )

            file.flush()
            os.fsync(file.fileno())

        temporary_path.replace(path)

    # ------------------------------------------------------------------
    # Conversion vers CheckpointTuple
    # ------------------------------------------------------------------

    def _build_checkpoint_tuple(
        self,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
        record: dict[str, Any],
        storage: dict[str, Any],
    ) -> CheckpointTuple:
        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

        parent_checkpoint_id = record.get(
            "parent_checkpoint_id"
        )

        parent_config: RunnableConfig | None = None

        if parent_checkpoint_id:
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_checkpoint_id,
                }
            }

        checkpoint = self._deserialize(record["checkpoint"])
        metadata = self._deserialize(record["metadata"])

        pending_writes: list[
            tuple[str, str, Any]
        ] = []

        writes_for_checkpoint = storage.get(
            "writes",
            {},
        ).get(
            checkpoint_id,
            {},
        )

        for write_record in writes_for_checkpoint.values():
            pending_writes.append(
                (
                    write_record["task_id"],
                    write_record["channel"],
                    self._deserialize(
                        write_record["value"]
                    ),
                )
            )

        return CheckpointTuple(
            config,
            checkpoint,
            metadata,
            parent_config,
            pending_writes,
        )

    # ------------------------------------------------------------------
    # API synchrone
    # ------------------------------------------------------------------

    def get_tuple(
        self,
        config: RunnableConfig,
    ) -> CheckpointTuple | None:
        thread_id = self._get_thread_id(config)
        checkpoint_ns = self._get_checkpoint_namespace(config)
        requested_id = self._get_checkpoint_id(config)
        path = self._path(config)

        with self._sync_lock:
            storage = self._read_storage(path)

        checkpoints = storage["checkpoints"]

        if not checkpoints:
            return None

        checkpoint_id = requested_id

        if checkpoint_id is None:
            checkpoint_id = max(checkpoints)

        record = checkpoints.get(checkpoint_id)

        if record is None:
            return None

        return self._build_checkpoint_tuple(
            thread_id=thread_id,
            checkpoint_ns=checkpoint_ns,
            checkpoint_id=checkpoint_id,
            record=record,
            storage=storage,
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if config is None:
            return iter(())

        thread_id = self._get_thread_id(config)
        checkpoint_ns = self._get_checkpoint_namespace(config)
        path = self._path(config)

        with self._sync_lock:
            storage = self._read_storage(path)

        checkpoint_ids = sorted(
            storage["checkpoints"],
            reverse=True,
        )

        if before is not None:
            before_id = self._get_checkpoint_id(before)

            if before_id is not None:
                checkpoint_ids = [
                    checkpoint_id
                    for checkpoint_id in checkpoint_ids
                    if checkpoint_id < before_id
                ]

        yielded = 0

        for checkpoint_id in checkpoint_ids:
            record = storage["checkpoints"][checkpoint_id]
            metadata = self._deserialize(record["metadata"])

            if filter is not None and not all(
                metadata.get(key) == value
                for key, value in filter.items()
            ):
                continue

            yield self._build_checkpoint_tuple(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                checkpoint_id=checkpoint_id,
                record=record,
                storage=storage,
            )

            yielded += 1

            if limit is not None and yielded >= limit:
                break

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, str | int | float],
    ) -> RunnableConfig:
        thread_id = self._get_thread_id(config)
        checkpoint_ns = self._get_checkpoint_namespace(config)
        parent_checkpoint_id = self._get_checkpoint_id(config)

        checkpoint_id = str(checkpoint["id"])
        path = self._path(config)

        record = {
            "checkpoint": self._serialize(checkpoint),
            "metadata": self._serialize(metadata),
            "parent_checkpoint_id": parent_checkpoint_id,
            "new_versions": self._serialize(new_versions),
        }

        with self._sync_lock:
            storage = self._read_storage(path)

            storage["checkpoints"][checkpoint_id] = record

            self._write_storage(path, storage)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        checkpoint_id = self._get_checkpoint_id(config)

        if checkpoint_id is None:
            raise ValueError(
                "Cannot store writes without checkpoint_id"
            )

        path = self._path(config)

        with self._sync_lock:
            storage = self._read_storage(path)

            checkpoint_writes = storage[
                "writes"
            ].setdefault(
                checkpoint_id,
                {},
            )

            for index, (channel, value) in enumerate(writes):
                write_key = (
                    f"{task_id}:{task_path}:{index}:{channel}"
                )

                checkpoint_writes[write_key] = {
                    "task_id": task_id,
                    "task_path": task_path,
                    "channel": channel,
                    "value": self._serialize(value),
                }

            self._write_storage(path, storage)

    def delete_thread(self, thread_id: str) -> None:
        safe_thread = self._safe_filename(str(thread_id))
        pattern = f"{safe_thread}__*.json"

        with self._sync_lock:
            for path in self.directory.glob(pattern):
                path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # API asynchrone
    # ------------------------------------------------------------------

    async def aget_tuple(
        self,
        config: RunnableConfig,
    ) -> CheckpointTuple | None:
        path = self._path(config)
        lock = self._get_async_lock(path)

        async with lock:
            return await asyncio.to_thread(
                self.get_tuple,
                config,
            )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        if config is None:
            return

        path = self._path(config)
        lock = self._get_async_lock(path)

        async with lock:
            checkpoints = await asyncio.to_thread(
                lambda: list(
                    self.list(
                        config,
                        filter=filter,
                        before=before,
                        limit=limit,
                    )
                )
            )

        for checkpoint_tuple in checkpoints:
            yield checkpoint_tuple

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, str | int | float],
    ) -> RunnableConfig:
        path = self._path(config)
        lock = self._get_async_lock(path)

        async with lock:
            return await asyncio.to_thread(
                self.put,
                config,
                checkpoint,
                metadata,
                new_versions,
            )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        path = self._path(config)
        lock = self._get_async_lock(path)

        async with lock:
            await asyncio.to_thread(
                self.put_writes,
                config,
                writes,
                task_id,
                task_path,
            )

    async def adelete_thread(
        self,
        thread_id: str,
    ) -> None:
        await asyncio.to_thread(
            self.delete_thread,
            thread_id,
        )