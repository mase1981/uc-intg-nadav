"""
NAD AV driver for Unfolded Circle integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import logging

from ucapi_framework import BaseIntegrationDriver

from intg_nadav.config import NADDeviceConfig
from intg_nadav.device import NADDevice
from intg_nadav.media_player import NADMediaPlayer
from intg_nadav.select import (
    NADPresetSelect,
    NADRepeatSelect,
    NADSourceSelect,
    NADSpeakerASelect,
    NADSpeakerBSelect,
)
from intg_nadav.sensor import (
    NADConnectionSensor,
    NADModelSensor,
    NADSourceSensor,
    NADVersionSensor,
)

_LOG = logging.getLogger(__name__)


class NADDriver(BaseIntegrationDriver[NADDevice, NADDeviceConfig]):
    """NAD AV integration driver."""

    def __init__(self) -> None:
        super().__init__(
            device_class=NADDevice,
            entity_classes=[
                NADMediaPlayer,
                NADSourceSelect,
                NADModelSensor,
                NADSourceSensor,
                NADConnectionSensor,
                lambda cfg, dev: [NADVersionSensor(cfg, dev)] if not cfg.is_bluos else [],
                lambda cfg, dev: [NADPresetSelect(cfg, dev), NADRepeatSelect(cfg, dev)] if cfg.is_bluos else [],
                lambda cfg, dev: [NADSpeakerASelect(cfg, dev), NADSpeakerBSelect(cfg, dev)] if not cfg.is_bluos else [],
            ],
            driver_id="nadav",
        )
