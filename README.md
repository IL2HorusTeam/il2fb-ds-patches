# IL-2 Sturmovik: Forgotten Battles: Dedicated Server patches

This is a mirror of [official patches](http://forum.1cpublishing.eu/forumdisplay.php?f=202) for dedicated server of «IL-2 Sturmovik: Forgotten Battles» flight simulator.

Contains original ``EXE`` files.

Also includes ``ZIP`` versions, which are just repacked versions of original ``EXE``. Useful for non-Windows systems.


## Patches

Patches are listed on [the releases page](https://github.com/IL2HorusTeam/il2fb-ds-patches/releases).


## Docker images

Docker images are available as [``il2horusteam/il2ds``](https://hub.docker.com/r/il2horusteam/il2ds).


## Downloader

This repository contains a downloader of server's patches ``il2fb_download_ds.py``.

The downloader allows to fetch both ``EXE`` and ``ZIP`` versions of patches.


### Installation

Depends on Python 3.7+.

The downloader runs as a local script, hence clone this repo or download the following files:

* ``il2fb_download_ds.py``
* ``requirements.txt``

Installation of dependencies:

``` shell
pip install -r requirements.txt
```


### Usage synopsis

```
usage: il2fb_download_ds.py [-h] [-v VERSION_SPEC [VERSION_SPEC ...]]
                            [--with-zip] [--no-zip] [--with-exe] [--no-exe]
                            [-o OUTPUT_DIR]

Download patches for dedicated server of IL-2 FB

optional arguments:
  -h, --help            show this help message and exit
  -v VERSION_SPEC [VERSION_SPEC ...], --version VERSION_SPEC [VERSION_SPEC ...]
                        versions to download, all versions are downloaded by
                        default; separate mulpiple values with space; ex:
                        '4.14.1', ex: '>=4.12', ex: '<3', ex: '==4.12.*', ex:
                        '>=4.12,<4.13', ex: '==4.11.1' '==4.10.1'
  --with-zip            download repacked ZIP versions of pathes (enabled by
                        default)
  --no-zip              do not download repacked ZIP versions of pathes
  --with-exe            download original EXE versions of pathes (enabled by
                        default)
  --no-exe              do not download original EXE versions of pathes
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        output directory for downloaded files (default:
                        './patches')
```


### Checksums

The downloader fetches MD5 checksums for every patch. However, it's up to the user to check patches against their checksums.


### Usage examples

Download all patches, both ``EXE`` and ``ZIP``:

``` shell
./il2fb_download_ds.py
```

Download all patches, ``EXE``-only:

``` shell
./il2fb_download_ds.py --no-zip
```

Download all patches, ``ZIP``-only:

``` shell
./il2fb_download_ds.py --no-exe
```

Download ``ZIP`` patch of version '4.14.1':

``` shell
./il2fb_download_ds.py --no-exe -v '4.14.1'
```

Download all ``ZIP`` patches of version '4.12' and newer:

``` shell
./il2fb_download_ds.py --no-exe -v '>=4.12'
```

Download all ``ZIP`` patches older that version '3':

``` shell
./il2fb_download_ds.py --no-exe -v '<3'
```

Download all ``ZIP`` patches of version '4.12.*' ('4.12', '4.12.1', '4.12.2'):

``` shell
./il2fb_download_ds.py --no-exe -v '4.12.*'
```

The same as above:

``` shell
./il2fb_download_ds.py --no-exe -v '>=4.12,<4.13'
```

Download all ``ZIP`` patches between versions '4.09' and '4.12' inclusive:

``` shell
./il2fb_download_ds.py --no-exe -v '>=4.09,<=4.12'
```

Download ``ZIP`` patches of versions '4.11.1' and '4.10.1':

``` shell
./il2fb_download_ds.py --no-exe -v '4.11.1' '4.10.1'
```


### Preview

![Downloader preview](./downloader.png?raw=true "Downloader preview")
