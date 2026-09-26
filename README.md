# CTFR

> Maintained fork of [UnaPibaGeek/ctfr](https://github.com/UnaPibaGeek/ctfr) with input validation, timeouts, tests, and modern packaging. See [CHANGELOG.md](CHANGELOG.md).

CTFR discovers subdomains from public [Certificate Transparency](https://certificate.transparency.dev/) logs through [crt.sh](https://crt.sh/). It does not use dictionaries or brute force.

## Requirements

- Python 3.9 or later
- [`requests`](https://pypi.org/project/requests/) (the only dependency)
- Internet access to `crt.sh`

## Quick start

CTFR is a single script. If you already have `requests`, there is nothing to install:

```bash
git clone https://github.com/RavenAsakura/ctfr.git
python3 ctfr.py -d example.com
```

If `requests` is missing, install it first:

```bash
python3 -m pip install -r requirements.txt
```

## Installation

Install the package if you want the `ctfr` command available anywhere, or if you plan to use CTFR regularly. A virtual environment keeps its dependencies separate from your system Python:

```bash
git clone https://github.com/RavenAsakura/ctfr.git
cd ctfr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

On Debian and Ubuntu, install the `python3-venv` package first if `python3 -m venv` fails. On Windows, activate with `.venv\Scripts\activate` instead.

For development, use an editable install so your changes take effect immediately:

```bash
python -m pip install -e .
```

## Usage

```text
ctfr -d DOMAIN_OR_URL [-o FILE] [--append] [--timeout SECONDS]
```

The target can be a domain or a complete URL:

```bash
ctfr -d example.com
ctfr -d https://example.com/path
ctfr -d example.com -o subdomains.txt
ctfr -d example.com -o subdomains.txt --append
```

By default, `--output` replaces the destination file with sorted, unique results. Use `--append` to preserve its contents and add only names that are not already present.

Without installing the package, run the script with `python3 ctfr.py` and the same options.

## Tests

The test suite does not make external network requests:

```bash
python -m unittest discover -s tests -v
```

## Changes

See [CHANGELOG.md](CHANGELOG.md) for the complete list of fixes, new features, behavior changes, validation performed, and known limitations.

## Responsible use

Certificate Transparency data is public, but you should only investigate systems when you have authorization to do so.

## License

CTFR is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## Credits

**Original author:** CTFR was created by Sheila A. Berta ([@UnaPibaGeek](https://www.twitter.com/UnaPibaGeek)). The original project is at [UnaPibaGeek/ctfr](https://github.com/UnaPibaGeek/ctfr).

**Maintainer of this fork:** [RavenAsakura](https://github.com/RavenAsakura), who authored the reliability fixes, tests, and packaging in [version 1.3.0](CHANGELOG.md).
