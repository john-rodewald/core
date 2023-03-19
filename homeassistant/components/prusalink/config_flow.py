"""Config flow for PrusaLink integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import ClientError
import async_timeout
from awesomeversion import AwesomeVersion, AwesomeVersionException
from pyprusalink import InvalidAuth, PrusaLink
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_KEY,
    API_KEY_AUTH,
    AUTH_STEP,
    AUTH_TYPE,
    DIGEST_AUTH,
    DOMAIN,
    HOST,
    PASSWORD,
    SETUP_STEP,
    USER,
)

_LOGGER = logging.getLogger(__name__)

DIGEST_AUTH_SCHEMA = vol.Schema(
    {
        USER: vol.Required(str),
        PASSWORD: vol.Required(str),
    }
)

API_KEY_AUTH_SCHEMA = vol.Schema(
    {
        API_KEY: vol.Required(str),
    }
)

SETUP_STEP_SCHEMA = vol.Schema(
    {
        vol.Required(HOST): str,
        vol.Required(AUTH_TYPE, default=DIGEST_AUTH): vol.In(
            (DIGEST_AUTH, API_KEY_AUTH)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> dict[str, str]:
    """Validate the user input allows us to connect.

    Data has the keys from SETUP_STEP_SCHEMA with values provided by the user.
    """

    api = PrusaLink(async_get_clientsession(hass), data[HOST], data[API_KEY])

    try:
        async with async_timeout.timeout(5):
            version = await api.get_version()

    except (asyncio.TimeoutError, ClientError) as err:
        _LOGGER.error("Could not connect to PrusaLink: %s", err)
        raise CannotConnect from err

    try:
        if AwesomeVersion(version["api"]) < AwesomeVersion("2.0.0"):
            raise NotSupported
    except AwesomeVersionException as err:
        raise NotSupported from err

    return {"title": version["hostname"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PrusaLink."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        print("starting user_step")
        if user_input is None:
            return self.async_show_form(
                step_id=SETUP_STEP,
                data_schema=SETUP_STEP_SCHEMA,
            )

        print("finishing user_step")
        if user_input[AUTH_TYPE] == DIGEST_AUTH:
            return await self.async_step_user_auth()
        return await self.async_step_api_key_auth()

    async def async_step_user_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authentication via user + password."""

        print("starting auth_step: user")
        if user_input is None:
            return self.async_show_form(
                step_id=AUTH_STEP, data_schema=DIGEST_AUTH_SCHEMA
            )

        host = user_input[HOST].rstrip("/")
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"

        data = {
            HOST: host,
            USER: user_input[USER],
            PASSWORD: user_input[PASSWORD],
        }
        errors = {}

        try:
            info = await validate_input(self.hass, data)
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
            return self.async_create_entry(title=info["title"], data=data)

        print("finishing auth_step: user")
        return self.async_show_form(
            step_id=SETUP_STEP, data_schema=SETUP_STEP_SCHEMA, errors=errors
        )

    async def async_step_api_key_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authentication via API key."""

        print("starting auth_step: apiKey")
        if user_input is None:
            return self.async_show_form(
                step_id=AUTH_STEP, data_schema=API_KEY_AUTH_SCHEMA
            )

        host = user_input[HOST].rstrip("/")
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"

        data = {
            HOST: host,
            API_KEY: user_input[API_KEY],
        }
        errors = {}

        try:
            info = await validate_input(self.hass, data)
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
            return self.async_create_entry(title=info["title"], data=data)

        print("finishing auth_step: apiKey")
        return self.async_show_form(
            step_id=SETUP_STEP, data_schema=SETUP_STEP_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class NotSupported(HomeAssistantError):
    """Error to indicate we cannot connect."""
