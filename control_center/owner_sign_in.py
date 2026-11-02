"""Microsoft owner authentication. No operator decision is made by this module."""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from api_client import APIError

DEFAULT_CLIENT_ID = "dc7101d3-3bb7-462f-92e8-374958f4ddb5"
RESOURCE_TENANT = "38de9dec-d800-439b-a669-60f628a90e72"
AUTHORITY = "https://login.microsoftonline.com/" + RESOURCE_TENANT + "/oauth2/v2.0/"
SHARED_SCOPES = "User.Read Files.ReadWrite.All offline_access"

def explain_sign_in_error(description):
    code = re.search(r"\bAADSTS(?:90094|90093|900941)\b", description)
    if not code:
        return description
    return ("Microsoft requires ATTAIR administrator approval for this sign-in. "
            "Approving an email in the Access Panel does not grant the app this Microsoft permission. "
            "Sign-in cannot continue until ATTAIR authorizes the app. Error: " + code.group() + ".")

def microsoft_post(endpoint, fields):
    request = urllib.request.Request(
        AUTHORITY + endpoint,
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            return json.load(error)
        except ValueError:
            raise APIError("Microsoft sign-in is temporarily unavailable.") from None
        finally:
            error.close()
    except (OSError, ValueError):
        raise APIError("Cannot connect to Microsoft sign-in. Check your internet connection.") from None

class MicrosoftOwnerSignIn:
    def __init__(self, client_id=DEFAULT_CLIENT_ID, post=microsoft_post, clock=time.monotonic,
                 scope="User.Read Files.ReadWrite offline_access"):
        self.client_id = client_id
        self.post = post
        self.clock = clock
        self.scope = scope

    def begin(self):
        result = self.post("devicecode", {"client_id": self.client_id, "scope": self.scope})
        required = ("device_code", "user_code", "verification_uri", "expires_in")
        if not all(result.get(name) for name in required):
            raise APIError(explain_sign_in_error(result.get("error_description", "Microsoft could not start owner sign-in.")))
        uri = urllib.parse.urlsplit(result["verification_uri"])
        host = uri.hostname or ""
        if uri.scheme != "https" or not (host == "microsoft.com" or
            host.endswith(".microsoft.com") or host == "login.microsoftonline.com"):
            raise APIError("Microsoft returned an unexpected sign-in address.")
        return result

    def finish(self, challenge, cancelled):
        deadline = self.clock() + int(challenge["expires_in"])
        interval = max(1, int(challenge.get("interval", 5)))
        while self.clock() < deadline:
            if cancelled.wait(interval):
                raise APIError("Owner sign-in cancelled.")
            result = self.post("token", {"client_id": self.client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": challenge["device_code"]})
            if result.get("access_token"):
                if cancelled.is_set():
                    raise APIError("Owner sign-in cancelled.")
                return result
            error = result.get("error")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            if error in ("authorization_declined", "access_denied"):
                raise APIError(explain_sign_in_error(result.get("error_description", "Microsoft sign-in was declined.")))
            if error == "expired_token":
                break
            raise APIError(explain_sign_in_error(result.get("error_description", "Microsoft sign-in could not finish.")))
        raise APIError("The Microsoft sign-in code expired. Start sign-in again.")


class MicrosoftTokenSession:
    """Use Microsoft's expiry metadata; never infer identity from an opaque token."""
    def __init__(self, tokens, post=microsoft_post, clock=time.time):
        self.tokens = dict(tokens)
        self.post = post
        self.clock = clock
        if self.tokens.get("tenant_id") != RESOURCE_TENANT:
            raise APIError("Sign in again to connect to the ATTAIR Microsoft tenant.", 401)

    @classmethod
    def from_result(cls, result, **kwargs):
        clock = kwargs.get("clock", time.time)
        tokens = cls.token_metadata(result, clock())
        return cls(tokens, **kwargs)

    @staticmethod
    def token_metadata(result, now, previous=None):
        previous = previous or {}
        try:
            lifetime = int(result["expires_in"])
            access = result["access_token"]
            if not isinstance(access, str) or not access or lifetime <= 0:
                raise ValueError()
            if result.get("token_type", "Bearer").lower() != "bearer":
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise APIError("Microsoft did not return valid token expiry metadata.", 401) from None
        return {"access_token": access, "refresh_token": result.get("refresh_token") or previous.get("refresh_token", ""),
                "scope": result.get("scope", previous.get("scope", "")),
                "expires_at": now + lifetime, "tenant_id": RESOURCE_TENANT}

    def __call__(self):
        if self.tokens.get("access_token") and self.clock() + 60 < self.tokens.get("expires_at", 0):
            return self.tokens["access_token"]
        refresh = self.tokens.get("refresh_token")
        if not refresh:
            raise APIError("Microsoft sign-in expired. Sign in again.", 401)
        # Omit scope to retain the original consent, without expanding permissions.
        result = self.post("token", {"client_id": DEFAULT_CLIENT_ID, "grant_type": "refresh_token", "refresh_token": refresh})
        if result.get("error"):
            raise APIError(explain_sign_in_error(result.get("error_description", "Microsoft could not refresh sign-in.")), 401)
        self.tokens = self.token_metadata(result, self.clock(), self.tokens)
        return self.tokens["access_token"]

    def snapshot(self):
        return dict(self.tokens)
