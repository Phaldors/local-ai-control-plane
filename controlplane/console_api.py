"""The human channel: a small HTTP API for reviewing and deciding escalations.

This is the only place an escalation gets decided, and it is deliberately separate from the MCP
server: the model talks to the MCP server and never to this API. A shared reviewer token protects
it (a demo stand-in for real authentication). Approving first re-checks hard policy in the back
office, so a reviewer cannot approve something the rules forbid; only the "needs a human" part is
overridden.

Run: python -m controlplane.console_api --db escalations.db --port 8765   (token from CONSOLE_TOKEN)
"""

import argparse
import os
import secrets
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from controlplane.backoffice import BackOffice
from controlplane.escalations import AlreadyDecided, Escalation, EscalationStore, NotFound


class Approve(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class Reject(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=500)


def create_app(
    store: EscalationStore,
    office: BackOffice,
    token: str,
    allowed_origins: list[str] | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Escalation review console", docs_url=None, redoc_url=None)
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["X-Reviewer-Token", "Content-Type"],
        )

    def authorize(x_reviewer_token: Annotated[str | None, Header()] = None) -> None:
        if not x_reviewer_token or not secrets.compare_digest(x_reviewer_token, token):
            raise HTTPException(status_code=401, detail="invalid reviewer token")

    def view(escalation: Escalation) -> dict[str, Any]:
        item = escalation.as_dict()
        item["facts"] = office.facts(escalation)
        if escalation.status == "pending":
            refusal = office.check(escalation)
            item["approvable"] = refusal is None
            item["blocked_by"] = refusal["blocked_by"] if refusal else None
            item["blocked_message"] = refusal["message"] if refusal else None
        else:
            item["approvable"] = False
            item["blocked_by"] = None
            item["blocked_message"] = None
        return item

    def load(esc_id: str) -> Escalation:
        try:
            return store.get(esc_id)
        except NotFound:
            raise HTTPException(status_code=404, detail=f"{esc_id} not found") from None

    guarded = [Depends(authorize)]

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/escalations", dependencies=guarded)
    def list_escalations(status: str | None = None) -> dict[str, Any]:
        if status not in (None, "pending", "approved", "rejected"):
            raise HTTPException(
                status_code=422, detail="status must be pending, approved or rejected"
            )
        return {"items": [view(e) for e in store.list_escalations(status)]}  # type: ignore[arg-type]

    @app.get("/api/escalations/{esc_id}", dependencies=guarded)
    def get_escalation(esc_id: str) -> dict[str, Any]:
        return {**view(load(esc_id)), "events": store.events(esc_id)}

    @app.post("/api/escalations/{esc_id}/approve", dependencies=guarded)
    def approve(esc_id: str, body: Approve) -> dict[str, Any]:
        escalation = load(esc_id)
        if escalation.status != "pending":
            raise HTTPException(status_code=409, detail=f"{esc_id} is already {escalation.status}")
        refusal = office.check(escalation)
        if refusal is not None:
            store.record(esc_id, "approval_refused", body.reviewer, refusal["message"], refusal)
            raise HTTPException(
                status_code=409,
                detail=f"cannot approve: {refusal['blocked_by']} ({refusal['message']})",
            )
        try:
            decided = store.decide(esc_id, "approved", body.reviewer, body.note)
        except AlreadyDecided:
            raise HTTPException(status_code=409, detail=f"{esc_id} is already decided") from None
        result = office.execute(decided)
        store.record(
            esc_id,
            "executed" if result["executed"] else "execution_failed",
            "back-office",
            None,
            result,
        )
        return {"escalation": view(decided), "result": result}

    @app.post("/api/escalations/{esc_id}/reject", dependencies=guarded)
    def reject(esc_id: str, body: Reject) -> dict[str, Any]:
        load(esc_id)
        try:
            decided = store.decide(esc_id, "rejected", body.reviewer, body.reason)
        except AlreadyDecided:
            raise HTTPException(status_code=409, detail=f"{esc_id} is already decided") from None
        return {"escalation": view(decided)}

    @app.get("/api/events", dependencies=guarded)
    def events(escalation_id: str | None = None) -> dict[str, Any]:
        return {"events": store.events(escalation_id)}

    if static_dir is not None and static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="console")
    return app


def main() -> None:
    parser = argparse.ArgumentParser(prog="controlplane.console_api")
    parser.add_argument("--db", type=Path, default=Path("escalations.db"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--static", type=Path, default=Path("console/dist"))
    parser.add_argument(
        "--origin", action="append", default=["http://localhost:5173"], help="allowed CORS origin"
    )
    args = parser.parse_args()
    token = os.environ.get("CONSOLE_TOKEN")
    if not token:
        raise SystemExit(
            "set CONSOLE_TOKEN (the shared reviewer token); the API refuses to run open"
        )
    app = create_app(EscalationStore(args.db), BackOffice(), token, args.origin, args.static)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
