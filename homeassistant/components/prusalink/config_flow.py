"""Config flow for PrusaLink integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from aiohttp import ClientError
import async_timeout
from pyprusalink import (
    API_KEY,
    API_KEY_AUTH,
    AUTH,
    AUTH_TYPE,
    DIGEST_AUTH,
    HOST,
    PASSWORD,
    USER,
    InvalidAuth,
    LinkConfiguration,
    PrusaLink,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.httpx_client import get_async_client

from .const import API_KEY_AUTH_STEP, DIGEST_AUTH_STEP, DOMAIN, USER_STEP

_LOGGER = logging.getLogger(__name__)

DIGEST_AUTH_SCHEMA = vol.Schema(
    {
        AUTH_TYPE: DIGEST_AUTH,
        vol.Required(HOST): str,
        USER: vol.Required(str),
        PASSWORD: vol.Required(str),
    }
)

API_KEY_AUTH_SCHEMA = vol.Schema(
    {
        AUTH_TYPE: API_KEY_AUTH,
        vol.Required(HOST): str,
        API_KEY: vol.Required(str),
    }
)

USER_STEP_SCHEMA = vol.Schema(
    {
        vol.Required(AUTH_TYPE, default=DIGEST_AUTH): vol.In(
            (DIGEST_AUTH, API_KEY_AUTH)
        ),
    }
)


class ValidatedInputInfo(TypedDict):
    """Shape of validated user input."""

    title: str


async def validate_link_config(
    hass: HomeAssistant, data: LinkConfiguration
) -> ValidatedInputInfo:
    """Validate the user input allows us to connect."""

    link_config: LinkConfiguration = data
    api = PrusaLink(get_async_client(hass), link_config)

    try:
        async with async_timeout.timeout(5):
            version = await api.get_version()

    except (asyncio.TimeoutError, ClientError) as err:
        _LOGGER.error("Could not connect to PrusaLink: %s", err)
        raise CannotConnect from err

    # try:
    #     if AwesomeVersion(version["api"]) < AwesomeVersion("2.0.0"):
    #         raise NotSupported
    # except AwesomeVersionException as err:
    #     raise NotSupported from err

    return {"title": version["hostname"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PrusaLink."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        if user_input is None:
            return self.async_show_form(
                step_id=USER_STEP,
                data_schema=USER_STEP_SCHEMA,
            )

        if user_input[AUTH_TYPE] == DIGEST_AUTH:
            return await self.async_step_digest_auth()
        return await self.async_step_api_key_auth()

    async def async_step_digest_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authentication via user + password."""

        if user_input is None:
            return self.async_show_form(
                step_id=DIGEST_AUTH_STEP, data_schema=DIGEST_AUTH_SCHEMA
            )

        link_config = get_link_config(user_input | {AUTH_TYPE: DIGEST_AUTH})
        errors = {}

        try:
            info = await validate_link_config(self.hass, link_config)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except NotSupported:
            errors["base"] = "not_supported"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=link_config)

        return self.async_show_form(
            step_id=USER_STEP, data_schema=USER_STEP_SCHEMA, errors=errors
        )

    async def async_step_api_key_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authentication via API key."""

        if user_input is None:
            return self.async_show_form(
                step_id=API_KEY_AUTH_STEP, data_schema=API_KEY_AUTH_SCHEMA
            )

        link_config = get_link_config(user_input | {AUTH_TYPE: API_KEY_AUTH})
        errors = {}

        try:
            info = await validate_link_config(self.hass, link_config)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except NotSupported:
            errors["base"] = "not_supported"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=link_config)

        return self.async_show_form(
            step_id=USER_STEP, data_schema=USER_STEP_SCHEMA, errors=errors
        )


def get_host(raw: str) -> str:
    """Format host from user input."""

    host = raw.rstrip("/")

    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"

    return host


def get_link_config(raw: dict[str, str]) -> LinkConfiguration:
    """Build LinkConfiguration depending on AUTH_TYPE.

    Input shape: API_KEY_AUTH_SCHEMA | DIGEST_AUTH_SCHEMA
    Output shape: LinkConfiguration
    """

    print("parsing to create link config:", raw)
    link_config: LinkConfiguration = None
    host = get_host(raw[HOST])

    if raw[AUTH_TYPE] == DIGEST_AUTH:
        link_config = {
            HOST: host,
            AUTH: {
                USER: raw[USER],
                PASSWORD: raw[PASSWORD],
                AUTH_TYPE: DIGEST_AUTH,
            },
        }

    if raw[AUTH_TYPE] == API_KEY_AUTH:
        link_config = {
            HOST: host,
            AUTH: {
                API_KEY: raw[API_KEY],
                AUTH_TYPE: API_KEY_AUTH,
            },
        }

    return link_config


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class NotSupported(HomeAssistantError):
    """Error to indicate we cannot connect."""
