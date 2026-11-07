"""
Thin client for the local sms-gammu-gateway container (which wraps a
physical GSM modem + SIM card via `gammu`).

Same rule as app/rag/llm_client.py: if the SMS gateway is unreachable, we
FAIL LOUDLY and explain why. There's no cloud SMS fallback — that would
break the "no cloud API dependency" requirement, and defeat the entire
reason this uses a physical modem in the first place (self-service SMS
opt-in needs to receive texts locally, which a cloud gateway can't do
without a public webhook server).
"""
import requests

from app.config import settings


class SmsGatewayUnavailableError(Exception):
    """Raised when the local SMS gateway (gammu + modem) can't be reached."""


def send_sms(phone_number: str, text: str) -> None:
    url = f"{settings.sms_gateway_base_url}/sms"
    try:
        response = requests.post(
            url,
            json={"text": text, "number": phone_number},
            auth=(settings.sms_gateway_user, settings.sms_gateway_password),
            timeout=settings.sms_gateway_timeout_seconds,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise SmsGatewayUnavailableError(
            "Could not reach the local SMS gateway. Make sure the "
            "sms-gateway container is running and the GSM modem is "
            "plugged in and detected (see docker-compose.yml sms-gateway "
            "service for setup notes)."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise SmsGatewayUnavailableError(
            f"SMS gateway did not respond within "
            f"{settings.sms_gateway_timeout_seconds}s — the modem may be "
            "busy or have lost signal."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise SmsGatewayUnavailableError(f"SMS gateway returned an error: {exc}") from exc


def fetch_inbox() -> list[dict]:
    """Returns unread inbound SMS messages, e.g. [{'Number': '+2547...',
    'Text': 'SUBSCRIBE LODWAR GOAT', 'Date': '...'}, ...]"""
    url = f"{settings.sms_gateway_base_url}/inbox"
    try:
        response = requests.get(
            url,
            auth=(settings.sms_gateway_user, settings.sms_gateway_password),
            timeout=settings.sms_gateway_timeout_seconds,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise SmsGatewayUnavailableError(
            "Could not reach the local SMS gateway to check for new messages."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise SmsGatewayUnavailableError(f"SMS gateway returned an error: {exc}") from exc

    return response.json()
