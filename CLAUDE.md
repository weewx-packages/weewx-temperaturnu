# weewx-temperaturnu

WeeWX RESTful uploader for temperatur.nu. Runtime module `bin/user/temperaturnu.py`, installer `install.py` (name `temperaturnu`). Independent continuation of LapplandsCohan/weewx-temperaturnu, see `ORIGIN.md`. Nothing is mirrored into this repository.

Python 3 only, WeeWX 5.x. Style of the file: no runtime annotations, types in Google-style docstrings. Preserve copyright notices and the GPL-3.0 `LICENSE`. Date changes to source files (note at the top of the file) and add a `changelog` entry.

Version lives in `install.py` and `VERSION` in the module. A test checks that they agree. README follows the weewx-packages schema and names no versions or archive URLs; installation links to the catalog page.

## Protocol

`GET https://www.temperatur.nu/rapportera.php?hash=HASH&t=TEMP`, temperature in degree C. Documented at https://www.temperatur.nu/info/rapportera-till-temperatur-nu/. The answer text (`ok! (12.3)`, `Fatal, failure! ...`) is observed, not documented. Do not probe the live server with made-up hashes.

## Phase

Alpha. A few fast smoke tests, no edge-case suite.

## Tests

`python -m pytest -q tests` in an environment with WeeWX and pytest, about 3 s. The tests use a local `http.server` and a temporary station directory, no network.
