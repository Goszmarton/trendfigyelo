"""Vékony belépő: a Trendfigyelő futtatása.

A tényleges orchestráció a trendfigyelo.futtato modulban él; ez a fájl csak
a parancssori indítást biztosítja.
"""

import sys

from trendfigyelo.futtato import main

if __name__ == "__main__":
    sys.exit(main())
