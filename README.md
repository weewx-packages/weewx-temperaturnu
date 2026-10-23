# weewx-temperaturnu

A WeeWX uploader for [temperatur.nu](https://www.temperatur.nu). It sends the outside temperature of every archive record to the report URL of your measuring point. It uploads no other observation.

This is a continuation of [LapplandsCohan/weewx-temperaturnu](https://github.com/LapplandsCohan/weewx-temperaturnu), which is derived from Matthew Wall's WeeWX uploaders. See `ORIGIN.md`.

## Requirements

- A measuring point on temperatur.nu with the reporting method "Rapporteringsurl". temperatur.nu shows the hash of the point on its page.
- A sensor that reports `outTemp`.

## Installation

Install `temperaturnu` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/temperaturnu.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

The installer adds the section below with a placeholder hash. Replace it with your own and restart WeeWX. While the placeholder is in place, nothing is uploaded.

## Configuration

```
[StdRESTful]
    [[TemperaturNu]]
        hash = TEMPERATURNU_HASH
```

| Option | Default | Meaning |
|---|---|---|
| `hash` | none | Hash of the measuring point. Required. The hash is not written to the log. |
| `enable` | `true` | Set to `false` to switch the uploader off. |
| `server_url` | `https://www.temperatur.nu/rapportera.php` | Report URL. |
| `post_interval` | `40` | Minimum seconds between two uploads. |
| `max_backlog` | `1` | Records that may wait in the queue before older ones are dropped. |
| `stale` | none | Age in seconds after which a record is not uploaded. |
| `timeout` | `60` | Seconds to wait for the server. |
| `max_tries` | `3` | Attempts per upload. |
| `retry_wait` | `5` | Seconds between attempts. |
| `log_success` | `true` | Log every upload. |
| `log_failure` | `true` | Log every failed upload. |
| `skip_upload` | `false` | Prepare the upload but do not send it. |

The temperature is sent in degrees Celsius with one decimal. A record without `outTemp` is skipped.

## Limitations

- Tested only against a local stand-in for the server, not against a measuring point on temperatur.nu.
- temperatur.nu answers every report with HTTP 200 and says in the text whether it took the value. The format of that text is not documented. The uploader counts an answer that starts with `ok` as success and logs anything else as a failed upload.
- temperatur.nu asks for a new value every 5 minutes or more often for air temperature. An archive interval longer than that reports less often.

## Development

```
python -m pytest -q tests
```

The tests need WeeWX and pytest in the Python environment.

## License

Copyright 2021 Konrad Skeri Ekblad. GNU General Public License v3.0, see `LICENSE`.
