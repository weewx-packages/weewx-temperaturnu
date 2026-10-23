# Copyright 2021 Konrad Skeri Ekblad
#
# Modified 2026-10-23 by weewx-packages: Python 3 only, Python 2 and WeeWX 3
#   fallbacks removed; the hash is masked in the debug URL; the answer of
#   temperatur.nu is checked; records without outTemp are not sent; the
#   default server URL uses https; the placeholder hash is not uploaded.
#   See the changelog.

"""
This is a weewx extension that uploads data to temperatur.nu.
https://temperatur.nu
Based on temperatur.nu documentation as of 09 August 2021. The report URL
was checked again on 23 October 2026 against
https://www.temperatur.nu/info/rapportera-till-temperatur-nu/

Minimal Configuration:
[StdRESTful]
    [[TemperaturNu]]
        hash = TEMPERATURNU_HASH
"""

import logging
import queue
import re
from urllib.parse import urlencode

import weewx
import weewx.manager
import weewx.restx
import weewx.units
from weeutil.weeutil import to_bool

VERSION = "0.2"

if int(weewx.__version__.split('.')[0]) < 4:
    raise weewx.UnsupportedFeature("weewx 4 is required, found %s" %
                                   weewx.__version__)

log = logging.getLogger(__name__)

# The installer writes this value into weewx.conf. It is not a real hash.
PLACEHOLDER_HASH = 'TEMPERATURNU_HASH'


class TemperaturNu(weewx.restx.StdRESTbase):
    def __init__(self, engine, config_dict):
        """This service recognizes standard restful options plus the following:
        hash: Temperatur.nu hash
        """
        super().__init__(engine, config_dict)
        log.info("service version is %s", VERSION)
        site_dict = weewx.restx.get_site_dict(config_dict, 'TemperaturNu', 'hash')
        if site_dict is None:
            return
        if site_dict['hash'] == PLACEHOLDER_HASH:
            # The installer leaves this value in weewx.conf. Uploading with
            # it would send requests for a hash that belongs to nobody.
            log.info("hash is still %s, data will not be uploaded", PLACEHOLDER_HASH)
            return
        site_dict['manager_dict'] = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], 'wx_binding')

        self.archive_queue = queue.Queue()
        self.archive_thread = TemperaturNuThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        # The hash is the credential for the report URL, so it is not logged.
        log.info("Data will be uploaded to temperatur.nu")

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class TemperaturNuThread(weewx.restx.RESTThread):

    _SERVER_URL = 'https://www.temperatur.nu/rapportera.php'

    # this data map supports the default database schema
    #       temperaturnu_name   weewx_name      format  multiplier
    _DATA_MAP = {'t':          ('outTemp',      '%.1f', 1.0),  # C
                }

    def __init__(self, q, hash, manager_dict,
                 server_url=_SERVER_URL, skip_upload=False,
                 post_interval=40, max_backlog=1, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5):
        """Initializer for the uploader thread.

        Args:
            q (queue.Queue): The queue that delivers the archive records.
            hash (str): The hash that temperatur.nu assigns to the measuring point.
            manager_dict (dict): Arguments for opening the database manager.
            server_url (str): URL of the report script. Default is
                'https://www.temperatur.nu/rapportera.php'.

        The other arguments are those of weewx.restx.RESTThread.
        """
        # A record without outTemp has nothing to report, so it is not sent.
        super().__init__(q,
                         protocol_name='TemperaturNu',
                         essentials={'outTemp': True},
                         manager_dict=manager_dict,
                         post_interval=post_interval,
                         max_backlog=max_backlog,
                         stale=stale,
                         log_success=log_success,
                         log_failure=log_failure,
                         max_tries=max_tries,
                         timeout=timeout,
                         retry_wait=retry_wait,
                         skip_upload=skip_upload)
        self.hash = hash
        self.server_url = server_url

    # calculate derived quantities and other values needed by temperatur.nu
    def get_record(self, record, dbm):
        rec = super().get_record(record, dbm)

        # put everything into units required by Temperatur.nu
        rec = weewx.units.to_METRICWX(rec)

        return rec

    def format_url(self, record):
        # put data into expected structure and format
        values = {
            'hash': self.hash,
            }
        for key in self._DATA_MAP:
            rkey = self._DATA_MAP[key][0]
            if rkey in record and record[rkey] is not None:
                v = record[rkey] * self._DATA_MAP[key][2]
                values[key] = self._DATA_MAP[key][1] % v
        url = self.server_url + '?' + urlencode(values)
        if weewx.debug >= 2:
            log.debug('url: %s' % re.sub(r"hash=[^&]*", "hash=XXX", url))
        return url

    def check_response(self, response):
        """Check the answer of temperatur.nu.

        The server answers HTTP 200 for every report. The text tells the
        outcome: 'ok! (12.3)' when the value was taken, and for example
        'Fatal, failure! ...' when it was not.

        Args:
            response (http.client.HTTPResponse): The response of the server.

        Raises:
            weewx.restx.FailedPost: The answer does not start with 'ok'.
        """
        answer = response.read().decode('utf-8', errors='replace').strip()
        if not answer.lower().startswith('ok'):
            raise weewx.restx.FailedPost("temperatur.nu answered: %s" % answer[:100])
