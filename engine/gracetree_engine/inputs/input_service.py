from __future__ import annotations

from pathlib import Path
from typing import Any

from ..storage.input_repository import InputRepository


class InputService:
    def __init__(self, approved_root: Path) -> None:
        self.approved_root = approved_root
        self.repository = InputRepository(approved_root)

    def register(self, job_id: str, source_paths: list[str]) -> dict[str, Any]:
        results = self.repository.register_batch(
            job_id, [Path(value) for value in source_paths]
        )
        return {"results": results, "inputs": self.repository.list_inputs(job_id)}

    def manage(self, job_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        action = payload["action"]
        input_id = payload["inputId"]
        if action == "assign_role":
            return self.repository.assign_role(job_id, input_id, payload["role"])
        if action == "remove":
            return self.repository.remove_input(job_id, input_id)
        return self.repository.replace_input(job_id, input_id, Path(payload["sourcePath"]))
