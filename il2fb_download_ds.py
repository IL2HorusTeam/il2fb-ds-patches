#!/usr/bin/env python3

import argparse
import asyncio
import datetime
import logging
import logging.config
import sys

from dataclasses import dataclass
from pathlib import Path

from typing import Dict
from typing import List
from typing import Optional
from typing import Text

import aiofile
import aiohttp
import semantic_version as semver
import tzlocal

from tqdm import tqdm
from yarl import URL


REPO_OWNER = "IL2HorusTeam"
REPO_NAME  = "il2fb-ds-patches"

REPO_BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
REPO_RELEASES_URL = f"{REPO_BASE_URL}/releases"
REPO_RELEASES_PER_PAGE = 100  # GitHub's default

ZIP_FILE_NAME_FMT     = "server-{version}.zip"
ZIP_MD5_FILE_NAME_FMT = "server-{version}.zip.md5"
EXE_FILE_NAME_FMT     = "server-{version}.exe"
EXE_MD5_FILE_NAME_FMT = "server-{version}.exe.md5"

CHUNK_SIZE = 2 ** 10  # 1 MiB


@dataclass
class FileSpec:
  url:  str
  path: Path
  size: int


@dataclass
class DownloadableFileSpec:
  target:     FileSpec
  target_md5: FileSpec


class LogRecordFormatter(logging.Formatter):
  converter = datetime.datetime.fromtimestamp
  _tz = tzlocal.get_localzone()

  def formatTime(self, record: logging.LogRecord, datefmt: str=None) -> str:
    ct = self.converter(record.created, self._tz)

    if datefmt:
      s = ct.strftime(datefmt)
    else:
      t = ct.strftime("%Y-%m-%d %H:%M:%S")
      s = "%s,%03d" % (t, record.msecs)

    return s


def setup_logging() -> None:
  logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
      'generic': {
        '()':      LogRecordFormatter,
        'format':  "%(asctime)s [%(levelname).1s] [%(process)s] %(message)s",
        'datefmt': "%Y-%m-%d %H:%M:%S.%f",
      },
    },
    'handlers': {
      'console': {
        'level':     "DEBUG",
        'formatter': "generic",
        'class':     "logging.StreamHandler",
        'stream':    "ext://sys.stdout",
      },
    },
    'loggers': {
      '': {
        'level': "DEBUG",
        'handlers': [
          'console',
        ],
      },
    },
  })


def make_args_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description="Download patches for dedicated server of IL-2 FB",
  )

  parser.add_argument(
    "-v", "--version",
    dest="version_spec",
    default=["*", ],
    nargs="+",
    help=(
      "versions to download, all versions are downloaded by default; "
      "separate mulpiple values with space; "
      "ex: '4.14.1', "
      "ex: '>=4.12', "
      "ex: '<3', "
      "ex: '==4.12.*', "
      "ex: '>=4.12,<4.13', "
      "ex: '==4.11.1' '==4.10.1'"
    ),
  )

  parser.add_argument(
    "--with-zip",
    dest="download_zip",
    action="store_true",
    help="download repacked ZIP versions of pathes (enabled by default)",
  )
  parser.add_argument(
    "--no-zip",
    dest="download_zip",
    action="store_false",
    help="do not download repacked ZIP versions of pathes",
  )
  parser.set_defaults(download_zip=True)

  parser.add_argument(
    "--with-exe",
    dest="download_exe",
    action="store_true",
    help="download original EXE versions of pathes (enabled by default)",
  )
  parser.add_argument(
    "--no-exe",
    dest="download_exe",
    action="store_false",
    help="do not download original EXE versions of pathes",
  )
  parser.set_defaults(download_exe=True)

  parser.add_argument(
    "-o", "--output-dir",
    metavar="OUTPUT_DIR",
    dest="output_dir_path",
    default="./patches",
    help="output directory for downloaded files (default: './patches')",
    type=Path,
  )

  return parser


async def get_releases_info(http_session: aiohttp.ClientSession) -> Dict:
  items = list()

  per_page = REPO_RELEASES_PER_PAGE
  page_no  = 0

  while True:
    params = dict(per_page=per_page, page=page_no)
    async with http_session.get(REPO_RELEASES_URL, params=params) as response:
      page_items = await response.json()
      items.extend(page_items)

    if len(page_items) < per_page:
      break
    else:
      page_no += 1

  return {
    item['tag_name']: item
    for item in items
  }


def filter_releases_info(
  releases_info: Dict,
  version_specs: semver.SimpleSpec,
) -> Dict:

  return {
    tag_name: info
    for tag_name, info in releases_info.items()
    if any(
      semver.Version.coerce(tag_name) in version_spec
      for version_spec in version_specs
    )
  }


def get_file_spec(
  assets: List[Dict],
  file_name: Text,
  md5_file_name: Text,
  output_dir_path: Path,
) -> Optional[DownloadableFileSpec]:

  params = dict()

  for item in assets:
    url = item['browser_download_url']
    url_file_name = Path(URL(url).path).name

    if url_file_name == file_name:
      params['target'] = FileSpec(
        url  = url,
        path = (output_dir_path / file_name),
        size = item['size'],
      )

    elif url_file_name == md5_file_name:
      params['target_md5'] = FileSpec(
        url  = url,
        path = (output_dir_path / md5_file_name),
        size = item['size'],
      )

    if 'target' in params and 'target_md5' in params:
      break

  if params:
    return DownloadableFileSpec(**params)


def make_file_specs(
  releases_info: Dict,
  download_zip: bool,
  download_exe: bool,
  output_dir_path: Path,
  log: logging.Logger,
) -> List[DownloadableFileSpec]:

  results = []

  for item in releases_info:
    version = item['tag_name']

    if download_zip:
      zip_file_name     = ZIP_FILE_NAME_FMT.format(version=version)
      zip_md5_file_name = ZIP_MD5_FILE_NAME_FMT.format(version=version)
      zip_file_spec = get_file_spec(
        assets=item['assets'],
        file_name=zip_file_name,
        md5_file_name=zip_md5_file_name,
        output_dir_path=output_dir_path,
      )
      if zip_file_spec:
        results.append(zip_file_spec)
      else:
        log.warning("no info about '%s'", zip_file_name)

    if download_exe:
      exe_file_name     = EXE_FILE_NAME_FMT.format(version=version)
      exe_md5_file_name = EXE_MD5_FILE_NAME_FMT.format(version=version)
      exe_file_spec = get_file_spec(
        assets=item['assets'],
        file_name=exe_file_name,
        md5_file_name=exe_md5_file_name,
        output_dir_path=output_dir_path,
      )
      if exe_file_spec:
        results.append(exe_file_spec)
      else:
        log.warning("no info about '%s'", exe_file_name)

  return results


async def download_file(
  http_session: aiohttp.ClientSession,
  file_spec: DownloadableFileSpec,
  position: int,
) -> None:

  if file_spec.target:
    request = http_session.get(file_spec.target.url)
    afp = aiofile.AIOFile(str(file_spec.target.path), "wb")
    progress = tqdm(
      desc=file_spec.target.path.name,
      total=file_spec.target.size,
      leave=False,
      miniters=1,
      unit="iB",
      unit_scale=True,
      unit_divisor=(2 ** 10),
      position=position,
      file=sys.stdout,
    )
    async with request as response, afp:
      with progress:
        writer = aiofile.Writer(afp)
        async for chunk in response.content.iter_chunked(CHUNK_SIZE):
          await writer(chunk)
          progress.update(len(chunk))

  if file_spec.target_md5:
    async with http_session.get(file_spec.target_md5.url) as response:
      content = await response.read()
      file_spec.target_md5.path.write_bytes(content)


async def run(
  http_session: aiohttp.ClientSession,
  version_specs: semver.SimpleSpec,
  download_zip: bool,
  download_exe: bool,
  output_dir_path: Path,
  log: logging.Logger,
) -> None:

  releases_info = await get_releases_info(http_session)
  log.info("available versions: %s", ", ".join(sorted(map(repr, releases_info.keys()))))

  releases_info = filter_releases_info(releases_info, version_specs)

  if releases_info:
    log.info("selected versions: %s", ", ".join(sorted(map(repr, releases_info.keys()))))
  else:
    raise ValueError("no versions match the query")

  releases_info = releases_info.values()

  file_specs = make_file_specs(
    releases_info=releases_info,
    download_zip=download_zip,
    download_exe=download_exe,
    output_dir_path=output_dir_path,
    log=log,
  )
  tasks = [
    asyncio.create_task(download_file(
      http_session=http_session,
      file_spec=file_spec,
      position=i,
    ))
    for i, file_spec in enumerate(file_specs)
  ]
  done, pending = await asyncio.wait(tasks)


async def main(
  args: argparse.Namespace,
  log: logging.Logger,
) -> int:

  version_specs = [
    semver.SimpleSpec(spec)
    for spec in args.version_spec
  ]
  output_dir_path = args.output_dir_path.absolute()
  output_dir_path.mkdir(parents=True, exist_ok=True)

  log.debug(
    "args: version_specs=%s, download_zip=%s, download_exe=%s, output_dir_path=%s",
    list(map(str, version_specs)),
    args.download_zip,
    args.download_exe,
    output_dir_path,
  )

  if not args.download_zip and not args.download_exe:
    log.error("both EXE and ZIP are disabled: at least one of them must be enabled")
    return -1

  async with aiohttp.ClientSession() as session:
    await run(
      http_session=session,
      version_specs=version_specs,
      download_zip=args.download_zip,
      download_exe=args.download_exe,
      output_dir_path=output_dir_path,
      log=log,
    )

  return 0


if __name__ == "__main__":
  parser = make_args_parser()
  args   = parser.parse_args()

  setup_logging()
  log = logging.root

  loop = asyncio.get_event_loop()

  try:
    log.info("downloader: run…")
    exit_code = loop.run_until_complete(main(args, log))
  except:
    exit_code = -1
    log.exception("downloader: failed")
  else:
    log.info("downloader: done")
  finally:
    sys.exit(exit_code)
