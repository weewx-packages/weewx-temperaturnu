import importlib.util
import pathlib

import configobj
import weecfg
import weecfg.extension
import weewx

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_installer_in_isolated_station(tmp_path):
    config = configobj.ConfigObj({
        'WEEWX_ROOT': str(tmp_path),
        'StdReport': {'SKIN_ROOT': 'skins', 'HTML_ROOT': 'public_html'},
        'Engine': {'Services': {name: [] for name in weewx.all_service_groups}}})
    config_path = tmp_path / 'weewx.conf'
    config.filename = str(config_path)
    config.write()
    engine = weecfg.extension.ExtensionEngine(str(config_path), config)
    engine.install_from_dir(str(ROOT), None)

    saved = configobj.ConfigObj(str(config_path))
    assert saved['StdRESTful']['TemperaturNu']['hash'] == 'TEMPERATURNU_HASH'
    assert 'user.temperaturnu.TemperaturNu' in saved['Engine']['Services']['restful_services']
    module = ROOT / 'bin/user/temperaturnu.py'
    assert (tmp_path / 'bin/user/temperaturnu.py').read_bytes() == module.read_bytes()


def test_installer_version_matches_module():
    installer = weecfg.get_extension_installer(str(ROOT))[1]
    spec = importlib.util.spec_from_file_location(
        'temperaturnu_version', ROOT / 'bin/user/temperaturnu.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert installer['version'] == module.VERSION
