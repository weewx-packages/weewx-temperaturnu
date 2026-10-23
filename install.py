# installer for WeeWX Temperatur.nu uploader
# Copyright 2021 Konrad Skeri Ekblad
#
# Modified 2026-10-23 by weewx-packages: version 0.2, removed the author
#   e-mail address, which belonged to the author of the uploader this one
#   is derived from.

from weecfg.extension import ExtensionInstaller

def loader():
    return TemperaturNuInstaller()

class TemperaturNuInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version="0.2",
            name='temperaturnu',
            description='Upload weather data to temperatur.nu.',
            author="Konrad Skeri Ekblad",
            restful_services='user.temperaturnu.TemperaturNu',
            config={
                'StdRESTful': {
                    'TemperaturNu': {
                        'hash': 'TEMPERATURNU_HASH'}}},
            files=[('bin/user', ['bin/user/temperaturnu.py'])]
            )
