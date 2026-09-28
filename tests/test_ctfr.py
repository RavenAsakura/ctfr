import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import ctfr


class NormalizeDomainTests(unittest.TestCase):
    def test_accepts_domains_and_urls(self):
        cases = {
            "example.com": "example.com",
            "www.example.com": "example.com",
            "https://example.com/path?q=1": "example.com",
            "https://www.example.com:443/path": "example.com",
            " EXAMPLE.COM. ": "example.com",
            "https://münich.example/path": "xn--mnich-kva.example",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(ctfr.normalize_domain(value), expected)

    def test_rejects_invalid_targets(self):
        for value in (
            "", "localhost", "https://", "bad_domain.example", "-bad.com",
            "ftp://example.com/file", "1.2", "127.0.0.1",
            "https://user:pass@example.com/path",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ctfr.normalize_domain(value)


class ExtractSubdomainsTests(unittest.TestCase):
    def test_splits_normalizes_filters_and_deduplicates(self):
        records = [
            {"name_value": "api.example.com\n*.dev.example.com"},
            {"name_value": "API.EXAMPLE.COM\nother.example.net"},
            {"name_value": "example.com."},
            {"irrelevant": "ignored"},
            "ignored",
        ]
        self.assertEqual(
            ctfr.extract_subdomains(records, "example.com"),
            ["api.example.com", "dev.example.com", "example.com"],
        )

    def test_rejects_unexpected_json(self):
        with self.assertRaises(ValueError):
            ctfr.extract_subdomains({"error": "busy"}, "example.com")


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield b'[{"name_value": "api.example.com"}]'


class FakeClient:
    def __init__(self):
        self.call = None

    def get(self, url, **kwargs):
        self.call = (url, kwargs)
        return FakeResponse()


class FetchSubdomainsTests(unittest.TestCase):
    def test_uses_query_parameters_headers_and_timeout(self):
        client = FakeClient()
        result = ctfr.fetch_subdomains("example.com", timeout=4.5, client=client)

        self.assertEqual(result, ["api.example.com"])
        self.assertEqual(client.call[0], ctfr.CRT_SH_URL)
        self.assertEqual(
            client.call[1]["params"], {"q": "%.example.com", "output": "json"}
        )
        self.assertEqual(client.call[1]["timeout"], 4.5)
        self.assertTrue(client.call[1]["stream"])
        self.assertIn("User-Agent", client.call[1]["headers"])

    def test_rejects_oversized_response(self):
        client = FakeClient()
        with patch.object(ctfr, "MAX_RESPONSE_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "size limit"):
                ctfr.fetch_subdomains("example.com", client=client)

    def test_rejects_response_after_total_timeout(self):
        client = FakeClient()
        with patch.object(ctfr.time, "monotonic", side_effect=[0, 2]):
            with self.assertRaisesRegex(ValueError, "total timeout"):
                ctfr.fetch_subdomains("example.com", timeout=1, client=client)


class CliTests(unittest.TestCase):
    def test_rejects_nonfinite_timeouts_and_append_without_output(self):
        for value in ("nan", "inf", "-inf", "0"):
            with self.subTest(value=value), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    ctfr.parse_args(["-d", "example.com", f"--timeout={value}"])
            self.assertEqual(error.exception.code, 2)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            ctfr.parse_args(["-d", "example.com", "--append"])
        self.assertEqual(error.exception.code, 2)

    def test_main_uses_normalized_target_and_saves_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.txt"
            with patch.object(ctfr, "fetch_subdomains", return_value=["api.example.com"]) as fetch:
                with redirect_stdout(io.StringIO()):
                    result = ctfr.main(["-d", "https://www.example.com/path", "-o", str(output)])
            self.assertEqual(result, 0)
            fetch.assert_called_once_with("example.com", ctfr.DEFAULT_TIMEOUT)
            self.assertEqual(output.read_text(encoding="utf-8"), "api.example.com\n")

    def test_main_reports_fetch_error_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.txt"
            with patch.object(ctfr, "fetch_subdomains", side_effect=ValueError("invalid JSON")):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errors:
                    result = ctfr.main(["-d", "example.com", "-o", str(output)])
            self.assertEqual(result, 1)
            self.assertIn("invalid JSON", errors.getvalue())
            self.assertFalse(output.exists())


class SaveSubdomainsTests(unittest.TestCase):
    def test_overwrites_with_sorted_unique_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.txt"
            output.write_text("old.example.com\n", encoding="utf-8")

            count = ctfr.save_subdomains(
                ["b.example.com", "a.example.com", "b.example.com"], output
            )

            self.assertEqual(count, 2)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "a.example.com\nb.example.com\n",
            )

    def test_append_writes_only_new_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.txt"
            output.write_text("a.example.com", encoding="utf-8")

            count = ctfr.save_subdomains(
                ["a.example.com", "b.example.com"], output, append=True
            )

            self.assertEqual(count, 1)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "a.example.com\nb.example.com\n",
            )

    def test_failed_replace_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.txt"
            output.write_text("old.example.com\n", encoding="utf-8")
            with patch.object(ctfr.os, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    ctfr.save_subdomains(["new.example.com"], output)
            self.assertEqual(output.read_text(encoding="utf-8"), "old.example.com\n")
            self.assertEqual(list(Path(directory).iterdir()), [output])


if __name__ == "__main__":
    unittest.main()
