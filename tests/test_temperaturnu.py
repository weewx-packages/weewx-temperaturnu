import http.server
import logging
import queue
import threading
import types

import configobj
import pytest
import weewx
import weewx.restx

import temperaturnu


class FakeServer:
    """A local stand-in for temperatur.nu that records the requests it gets."""

    def __init__(self, answer='ok! (0.0)'):
        self.requests = []
        self.answer = answer
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append((self.path, self.headers['User-Agent']))
                body = owner.answer.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=UTF-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:%d/rapportera.php' % self.httpd.server_port
        self.thread = threading.Thread(target=self.httpd.serve_forever)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.thread.join()
        self.httpd.server_close()


def make_thread(server_url, q=None, **options):
    return temperaturnu.TemperaturNuThread(
        q or queue.Queue(), 'abc123', None, server_url=server_url,
        retry_wait=0, **options)


def test_default_endpoint_is_the_documented_report_url():
    default = temperaturnu.TemperaturNuThread._SERVER_URL
    assert default == 'https://www.temperatur.nu/rapportera.php'


def test_archive_record_reaches_server_in_celsius():
    with FakeServer() as server:
        q = queue.Queue()
        thread = make_thread(server.url, q)
        thread.start()
        # 32 degree_F is 0 degree_C
        q.put({'dateTime': 1700000000, 'usUnits': weewx.US, 'outTemp': 32.0,
               'outHumidity': 55.0})
        q.put(None)
        thread.join(10)
        assert not thread.is_alive()
        assert [path for path, _ in server.requests] == ['/rapportera.php?hash=abc123&t=0.0']
        assert server.requests[0][1].startswith('weewx/')


def test_temperature_is_sent_with_one_decimal():
    with FakeServer() as server:
        thread = make_thread(server.url)
        thread.process_record({'dateTime': 1700000000, 'usUnits': weewx.METRIC,
                               'outTemp': -12.345}, None)
        assert server.requests[0][0] == '/rapportera.php?hash=abc123&t=-12.3'


def test_record_without_outtemp_is_not_sent():
    with FakeServer() as server:
        thread = make_thread(server.url)
        with pytest.raises(weewx.restx.AbortedPost):
            thread.process_record({'dateTime': 1700000000, 'usUnits': weewx.METRIC,
                                   'outTemp': None}, None)
        assert server.requests == []


def test_zero_degrees_is_sent():
    with FakeServer() as server:
        thread = make_thread(server.url)
        thread.process_record({'dateTime': 1700000000, 'usUnits': weewx.METRIC,
                               'outTemp': 0.0}, None)
        assert server.requests[0][0] == '/rapportera.php?hash=abc123&t=0.0'


def test_answer_that_is_not_ok_is_a_failed_post():
    with FakeServer('Fatal, failure! Kan inte matcha stad och id!') as server:
        thread = make_thread(server.url)
        with pytest.raises(weewx.restx.FailedPost) as error:
            thread.process_record({'dateTime': 1700000000, 'usUnits': weewx.METRIC,
                                   'outTemp': 3.0}, None)
        assert 'Fatal, failure!' in str(error.value)
        # An answer in the body is final, so the post is not repeated.
        assert len(server.requests) == 1


def test_skip_upload_sends_nothing():
    with FakeServer() as server:
        thread = make_thread(server.url, skip_upload='true')
        with pytest.raises(weewx.restx.AbortedPost):
            thread.process_record({'dateTime': 1700000000, 'usUnits': weewx.METRIC,
                                   'outTemp': 3.0}, None)
        assert server.requests == []


def test_debug_url_does_not_show_the_hash(monkeypatch, caplog):
    monkeypatch.setattr(weewx, 'debug', 2)
    thread = make_thread('http://127.0.0.1:1/rapportera.php')
    with caplog.at_level(logging.DEBUG):
        url = thread.format_url({'outTemp': 3.0})
    assert 'hash=abc123' in url
    assert 'abc123' not in caplog.text
    assert 'hash=XXX' in caplog.text


def make_service(tmp_path, monkeypatch, **options):
    monkeypatch.setattr(temperaturnu.TemperaturNuThread, 'start', lambda self: None)
    engine = types.SimpleNamespace(bind=lambda *args: None)
    site = {'hash': 'abc123'}
    site.update(options)
    config = configobj.ConfigObj({
        'WEEWX_ROOT': str(tmp_path),
        'StdRESTful': {'TemperaturNu': site},
        'DataBindings': {'wx_binding': {'database': 'archive',
                                        'manager': 'weewx.manager.Manager',
                                        'table_name': 'archive'}},
        'Databases': {'archive': {'database_type': 'SQLite',
                                  'database_name': 'weewx.sdb'}},
        'DatabaseTypes': {'SQLite': {'driver': 'weedb.sqlite',
                                     'SQLITE_ROOT': str(tmp_path)}}})
    return temperaturnu.TemperaturNu(engine, config)


def test_service_starts_the_uploader_without_logging_the_hash(tmp_path, monkeypatch, caplog):
    with caplog.at_level(logging.DEBUG):
        service = make_service(tmp_path, monkeypatch, post_interval='120')
    assert service.archive_thread.hash == 'abc123'
    assert service.archive_thread.post_interval == 120
    assert 'abc123' not in caplog.text


@pytest.mark.parametrize('options', [{'hash': 'TEMPERATURNU_HASH'},
                                     {'hash': 'replace_me'},
                                     {'enable': 'false'}])
def test_service_does_not_start_without_a_usable_hash(tmp_path, monkeypatch, options):
    assert not hasattr(make_service(tmp_path, monkeypatch, **options), 'archive_thread')
