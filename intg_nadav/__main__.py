"""
Entry point for running the integration as a module: python -m intg_nadav

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio

from intg_nadav import main

if __name__ == "__main__":
    asyncio.run(main())
