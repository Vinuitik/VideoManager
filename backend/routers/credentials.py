from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import services.credentials_store as store

router = APIRouter()


class CredentialIn(BaseModel):
    domain: str
    username: str
    password: str


class AgentInput(BaseModel):
    value: str


@router.post("/credentials")
async def upsert_credential(cred: CredentialIn):
    store.upsert(cred.domain, cred.username, cred.password)
    return {"status": "stored", "domain": cred.domain}


@router.get("/credentials")
async def list_credentials():
    return {"domains": store.list_domains()}


@router.delete("/credentials/{domain}")
async def delete_credential(domain: str):
    if not store.delete(domain):
        raise HTTPException(404, f"No credentials stored for '{domain}'")
    return {"status": "deleted", "domain": domain}
