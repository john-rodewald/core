"""Test the PrusaLink config flow."""
import asyncio
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.prusalink.config_flow import InvalidAuth
from homeassistant.components.prusalink.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form(hass: HomeAssistant, mock_version_api) -> None:
    """Test full flow's happy path."""

    initResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert initResult["type"] == FlowResultType.FORM
    assert initResult["errors"] is None

    authTypeStepResult = await hass.config_entries.flow.async_configure(
        initResult["flow_id"],
        {
            "authType": "ApiKeyAuth",
        },
    )
    await hass.async_block_till_done()

    assert authTypeStepResult["type"] == FlowResultType.FORM
    assert authTypeStepResult["errors"] is None

    with patch(
        "homeassistant.components.prusalink.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        authStepResult = await hass.config_entries.flow.async_configure(
            authTypeStepResult["flow_id"],
            {
                "host": "host",
                "authType": "ApiKeyAuth",
                "apiKey": "apiKey",
            },
        )
        await hass.async_block_till_done()

    assert authStepResult["type"] == FlowResultType.CREATE_ENTRY
    assert authStepResult["title"] == "PrusaMINI"
    assert authStepResult["data"] == {
        "host": "http://host",
        "auth": {
            "authType": "ApiKeyAuth",
            "apiKey": "apiKey",
        },
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test correct handling of invalid auth."""

    initResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    authTypeStepResult = await hass.config_entries.flow.async_configure(
        initResult["flow_id"],
        {
            "authType": "ApiKeyAuth",
        },
    )
    await hass.async_block_till_done()

    assert authTypeStepResult["type"] == FlowResultType.FORM
    assert authTypeStepResult["errors"] is None

    with patch(
        "homeassistant.components.prusalink.config_flow.PrusaLink.get_version",
        side_effect=InvalidAuth,
    ):
        authStepResult = await hass.config_entries.flow.async_configure(
            authTypeStepResult["flow_id"],
            {
                "host": "host",
                "authType": "ApiKeyAuth",
                "apiKey": "apiKey",
            },
        )
        await hass.async_block_till_done()

    assert authStepResult["type"] == FlowResultType.FORM
    assert authStepResult["errors"] == {"base": "invalid_auth"}


async def test_form_unknown(hass: HomeAssistant) -> None:
    """Test correct handling of unknown errors."""

    initResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    authTypeStepResult = await hass.config_entries.flow.async_configure(
        initResult["flow_id"],
        {
            "authType": "ApiKeyAuth",
        },
    )
    await hass.async_block_till_done()

    assert authTypeStepResult["type"] == FlowResultType.FORM
    assert authTypeStepResult["errors"] is None

    with patch(
        "homeassistant.components.prusalink.config_flow.PrusaLink.get_version",
        side_effect=ValueError,
    ):
        authStepResult = await hass.config_entries.flow.async_configure(
            authTypeStepResult["flow_id"],
            {
                "host": "host",
                "authType": "ApiKeyAuth",
                "apiKey": "apiKey",
            },
        )
        await hass.async_block_till_done()

    assert authStepResult["type"] == FlowResultType.FORM
    assert authStepResult["errors"] == {"base": "unknown"}


async def test_form_too_low_version(hass: HomeAssistant, mock_version_api) -> None:
    """Test correct handling of API version that is too low."""

    initResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_version_api["api"] = "1.2.0"

    authTypeStepResult = await hass.config_entries.flow.async_configure(
        initResult["flow_id"],
        {
            "authType": "ApiKeyAuth",
        },
    )
    await hass.async_block_till_done()

    assert authTypeStepResult["type"] == FlowResultType.FORM
    assert authTypeStepResult["errors"] is None

    authStepResult = await hass.config_entries.flow.async_configure(
        authTypeStepResult["flow_id"],
        {
            "host": "host",
            "authType": "ApiKeyAuth",
            "apiKey": "apiKey",
        },
    )
    await hass.async_block_till_done()

    assert authStepResult["type"] == FlowResultType.FORM
    assert authStepResult["errors"] == {"base": "not_supported"}


async def test_form_invalid_version_2(hass: HomeAssistant, mock_version_api) -> None:
    """Test correct handling of API version that is invalid."""

    initResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_version_api["api"] = "not a version"

    authTypeStepResult = await hass.config_entries.flow.async_configure(
        initResult["flow_id"],
        {
            "authType": "ApiKeyAuth",
        },
    )
    await hass.async_block_till_done()

    assert authTypeStepResult["type"] == FlowResultType.FORM
    assert authTypeStepResult["errors"] is None

    authStepResult = await hass.config_entries.flow.async_configure(
        authTypeStepResult["flow_id"],
        {
            "host": "host",
            "authType": "ApiKeyAuth",
            "apiKey": "apiKey",
        },
    )
    await hass.async_block_till_done()

    assert authStepResult["type"] == FlowResultType.FORM
    assert authStepResult["errors"] == {"base": "not_supported"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test correct handling of failed connection."""

    initResult = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    authTypeStepResult = await hass.config_entries.flow.async_configure(
        initResult["flow_id"],
        {
            "authType": "ApiKeyAuth",
        },
    )
    await hass.async_block_till_done()

    assert authTypeStepResult["type"] == FlowResultType.FORM
    assert authTypeStepResult["errors"] is None

    with patch(
        "homeassistant.components.prusalink.config_flow.PrusaLink.get_version",
        side_effect=asyncio.TimeoutError,
    ):
        authStepResult = await hass.config_entries.flow.async_configure(
            authTypeStepResult["flow_id"],
            {
                "host": "host",
                "authType": "ApiKeyAuth",
                "apiKey": "apiKey",
            },
        )
        await hass.async_block_till_done()

    assert authStepResult["type"] == FlowResultType.FORM
    assert authStepResult["errors"] == {"base": "cannot_connect"}
