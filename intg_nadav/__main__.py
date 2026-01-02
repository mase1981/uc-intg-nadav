"""
NAD AV Integration entry point.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import sys
import asyncio
from intg_nadav import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nIntegration stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting integration: {e}")
        sys.exit(1)