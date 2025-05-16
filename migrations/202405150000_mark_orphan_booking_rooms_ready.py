# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script to mark rooms with state='booking' and no guest as 'ready'
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        # 1. Find all rooms that are in booking state without a guest
        domain = [
            ('state', '=', 'booking'),
            ('current_guest_id', '=', False)
        ]

        rooms = env['hotel.room'].search(domain)

        if not rooms:
            _logger.info("No orphan booking rooms found to update")
            return

        # 2. Log details before update
        _logger.info(f"Found {len(rooms)} rooms to update from 'booking' to 'ready' state")
        _logger.debug("Room IDs to update: %s", rooms.ids)

        # 3. Update the state
        rooms.write({'state': 'ready'})

        # 4. Log completion
        _logger.info("Successfully updated %d rooms to 'ready' state", len(rooms))

    except Exception as e:
        _logger.error("Failed to update room states: %s", str(e))
        raise