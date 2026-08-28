import re

import httpx
import structlog

logger = structlog.get_logger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com"
LINKEDIN_TIMEOUT_SECONDS = 45
LINKEDIN_REST_VERSION = "202606"
_URN_PERSON = re.compile(r"^urn:li:person:(.+)$")
_URN_ORGANIZATION = re.compile(r"^urn:li:organization:(.+)$")
_URN_MEMBER = re.compile(r"^urn:li:member:-?\d+$")
_URN_COMPANY = re.compile(r"^urn:li:company:(\d+)$")


class LinkedinPublishError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def _build_linkedin_post_text(*, post_text: str, article_url: str | None) -> str:
    text = post_text.strip()
    if article_url and article_url not in text:
        if text:
            return f"{text}\n\n{article_url}"
        return article_url
    return text


def _invalid_author_urn_error() -> LinkedinPublishError:
    return LinkedinPublishError(
        "Invalid LINKEDIN_AUTHOR_URN. Use `urn:li:person:<id>` for your profile, "
        "`urn:li:organization:<numeric-id>` for a company page, or leave it empty to "
        "auto-detect your profile from LINKEDIN_ACCESS_TOKEN (requires openid + profile scopes).",
        retryable=False,
    )


def _normalize_author_urn(author_urn: str) -> str:
    value = author_urn.strip().strip('"').strip("'")
    if _URN_PERSON.match(value) or _URN_ORGANIZATION.match(value):
        return value
    member_match = _URN_MEMBER.match(value)
    if member_match:
        member_id = value.rsplit(":", maxsplit=1)[-1]
        return f"urn:li:person:{member_id}"
    company_match = _URN_COMPANY.match(value)
    if company_match:
        return f"urn:li:organization:{company_match.group(1)}"
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return f"urn:li:person:{value}"
    raise _invalid_author_urn_error()


def try_normalize_author_urn(author_urn: str | None) -> str | None:
    if not author_urn or not author_urn.strip():
        return None
    try:
        return _normalize_author_urn(author_urn)
    except LinkedinPublishError:
        return None


async def resolve_author_urn_from_token(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=float(LINKEDIN_TIMEOUT_SECONDS)) as client:
        response = await client.get(
            f"{LINKEDIN_API_BASE}/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code in (401, 403):
        raise LinkedinPublishError(
            "LinkedIn access token rejected while resolving author URN. "
            "For company-page posts, set LINKEDIN_AUTHOR_URN to "
            "urn:li:organization:<numeric-id> (or urn:li:company:<id>) and use a token "
            "with w_organization_social. For personal posts, leave AUTHOR_URN empty and "
            "regenerate the token with openid, profile, and w_member_social scopes.",
            retryable=False,
        )
    if response.status_code != 200:
        logger.error(
            "LinkedIn userinfo failed",
            status=response.status_code,
            body=response.text[:500],
        )
        raise LinkedinPublishError(
            f"Could not resolve LinkedIn author from token ({response.status_code}).",
            retryable=response.status_code >= 500 or response.status_code == 429,
        )

    payload = response.json()
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise LinkedinPublishError(
            "LinkedIn token did not return a profile id (sub). "
            "Ensure the token includes openid and profile scopes.",
            retryable=False,
        )
    return f"urn:li:person:{sub.strip()}"


async def resolve_author_urn_for_publish(
    *,
    access_token: str,
    author_urn: str | None,
) -> str:
    normalized = try_normalize_author_urn(author_urn)
    if normalized:
        return normalized
    if author_urn and author_urn.strip():
        logger.warning(
            "LINKEDIN_AUTHOR_URN is invalid; resolving author from access token",
        )
    else:
        logger.info("LINKEDIN_AUTHOR_URN not set; resolving author from access token")
    return await resolve_author_urn_from_token(access_token)


async def publish_post(
    *,
    access_token: str,
    author_urn: str,
    post_text: str,
    article_url: str | None = None,
) -> str | None:
    normalized_author_urn = _normalize_author_urn(author_urn)
    text = _build_linkedin_post_text(post_text=post_text, article_url=article_url)
    if not text and not article_url:
        raise LinkedinPublishError(
            "LinkedIn post text is empty. Add content before publishing.",
            retryable=False,
        )

    commentary = post_text.strip()
    if article_url and article_url in commentary:
        commentary = commentary.replace(article_url, "").strip()
    if not commentary:
        commentary = text.strip() if text else "Read the full article."

    payload: dict[str, object] = {
        "author": normalized_author_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if article_url:
        payload["content"] = {
            "article": {
                "source": article_url,
                "title": "Read full article",
            }
        }

    async with httpx.AsyncClient(timeout=float(LINKEDIN_TIMEOUT_SECONDS)) as client:
        response = await client.post(
            f"{LINKEDIN_API_BASE}/rest/posts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": LINKEDIN_REST_VERSION,
            },
            json=payload,
        )

    if response.status_code in (401, 403):
        raise LinkedinPublishError(
            "LinkedIn access token rejected. For company pages use w_organization_social "
            "and LINKEDIN_AUTHOR_URN=urn:li:organization:<id>. For personal profiles use "
            "openid, profile, w_member_social, and leave AUTHOR_URN empty to auto-detect.",
            retryable=False,
        )
    if response.status_code == 426:
        raise LinkedinPublishError(
            "LinkedIn API version is no longer supported. "
            f"Update DraftAI to the latest release (server sent: {response.text[:200]}).",
            retryable=False,
        )
    if response.status_code == 400:
        body_text = response.text
        if "organization" in body_text.lower() and "permission" in body_text.lower():
            raise LinkedinPublishError(
                "LinkedIn rejected the post: posting as a company page requires "
                "w_organization_social on LINKEDIN_ACCESS_TOKEN. Regenerate the token "
                "with that scope (you must be an admin of the page), or remove "
                "LINKEDIN_AUTHOR_URN to post to your personal profile instead.",
                retryable=False,
            )
    if response.status_code == 422:
        raise LinkedinPublishError(
            f"LinkedIn rejected the post: {response.text[:300]}",
            retryable=False,
        )
    if response.status_code not in (200, 201):
        logger.error(
            "LinkedIn publish failed",
            status=response.status_code,
            body=response.text[:500],
        )
        raise LinkedinPublishError(
            f"LinkedIn publish failed ({response.status_code}): {response.text[:200]}",
            retryable=response.status_code >= 500 or response.status_code == 429,
        )

    restli_id = response.headers.get("x-restli-id")
    if restli_id:
        return restli_id
    try:
        body = response.json()
    except Exception:
        return None
    post_id = body.get("id")
    return post_id if isinstance(post_id, str) and post_id else None
