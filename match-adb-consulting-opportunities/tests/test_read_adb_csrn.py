import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "read_adb_csrn.py"
SPEC = importlib.util.spec_from_file_location("read_adb_csrn", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

URL = "https://selfservice.adb.org/OA_HTML/adb/xxcrs/jsp/CsrnVw.jsp?sel=228464"
TITLE = "TA-10822 REG: Country Diagnostics - International (E-046186-009)"

PROFILE_HTML = f"""
<html><head><title>ADB CMS CSRN - {TITLE}</title></head><body>
<form method="POST" action="/OA_HTML/OA.jsp?page=profile&amp;selNo=228464">
  <input type="hidden" name="_FORM" value="token">
  <input type="hidden" name="event" value="Eoi">
  <input type="hidden" name="source" value="bEoi">
  <a id="lnk_tor" onclick="_uixspu('DefaultFormName',1,'tab_select','stlCsrn',0,0,
    {{'tab_tor':'true-token','_FORM_SUBMIT_BUTTON':'_fwkActBtnName_lnk_tor_tab_select-token',
      '_OA_SUB_TAB_INDEX':'1-token'}});return false;">Terms of Reference</a>
  <a id="lnk_cost" onclick="_uixspu('DefaultFormName',1,'tab_select','stlCsrn',0,0,
    {{'tab_cost':'true-token','_FORM_SUBMIT_BUTTON':'_fwkActBtnName_lnk_cost_tab_select-token',
      '_OA_SUB_TAB_INDEX':'2-token'}});return false;">Cost Estimate</a>
  <h1>{TITLE}</h1>
  <span>Date Published: <b>28-Aug-2026</b> Deadline of Submitting EOI:
    <b>03-Sep-2026 11:59 PM Manila local time</b></span>
  <h2>Selection Profile</h2>
  <div id="mcConsultantType"><span>Individual</span></div>
  <div id="mstSelectionMethod">Individual Consultant Selection (ICS)</div>
  <div id="mcConsultantSource"><span>International</span></div>
  <p>Profile details</p><p>Export to PDF</p>
</form></body></html>
"""

TOR_HTML = f"""
<html><body><h1>{TITLE}</h1>
<h2>Terms of Reference (Individual Consultant)</h2>
<p>Objective and Purpose of the Assignment</p><p>Diagnostic work</p>
<h3>Minimum Qualification Requirements</h3><p>Advanced economics degree</p>
<h3>Deliverables</h3><p>Diagnostic report</p>
<h3>Schedule and Places of Assignment (chronological and inclusive of travel)</h3>
<p>Home office, 20 days</p><p>Export to PDF</p>
</body></html>
"""

COST_HTML = f"""
<html><body><h1>{TITLE}</h1><table><tr><th>Cost Items</th></tr>
<tr><td>Amount in USD</td></tr><tr><td>TOTAL</td><td>9,129</td></tr></table>
<p>Export to PDF</p>
</body></html>
"""


class UrlValidationTests(unittest.TestCase):
    def test_accepts_only_canonical_record_url(self):
        record = MODULE.validate_record_url(URL)
        self.assertEqual(record.selection_id, "228464")
        self.assertEqual(record.canonical, URL)

    def test_rejects_noncanonical_or_unsafe_urls(self):
        invalid = [
            URL.replace("https://", "http://"),
            URL.replace("selfservice.adb.org", "example.com"),
            URL.replace("CsrnVw.jsp", "Other.jsp"),
            URL.replace("228464", "abc"),
            URL + "&other=1",
            URL + "#fragment",
            URL.replace("selfservice.adb.org", "selfservice.adb.org:443"),
        ]
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                with self.assertRaises(MODULE.InvalidRecordUrl):
                    MODULE.validate_record_url(candidate)


class ParserAndSafetyTests(unittest.TestCase):
    def test_parses_profile_metadata(self):
        profile = MODULE.parse_profile(PROFILE_HTML)
        self.assertEqual(profile["title"], TITLE)
        self.assertEqual(profile["published_date"], "28-Aug-2026")
        self.assertEqual(profile["deadline"], "03-Sep-2026 11:59 PM Manila local time")
        self.assertEqual(profile["consultant_type"], "Individual")
        self.assertEqual(profile["source"], "International")
        self.assertEqual(profile["selection_method"], "Individual Consultant Selection (ICS)")
        self.assertIn("Profile details", profile["profile"])

    def test_builds_only_verified_tab_submission(self):
        action, payload = MODULE.build_tab_submission(PROFILE_HTML, URL, "lnk_tor")
        self.assertEqual(action, "https://selfservice.adb.org/OA_HTML/OA.jsp?page=profile&selNo=228464")
        self.assertEqual(payload["event"], "tab_select")
        self.assertEqual(payload["source"], "stlCsrn")
        self.assertIn("lnk_tor_tab_select", payload["_FORM_SUBMIT_BUTTON"])
        self.assertNotEqual(payload["event"], "Eoi")
        self.assertNotEqual(payload["source"], "bEoi")

    def test_rejects_unapproved_action_path(self):
        unsafe = PROFILE_HTML.replace(
            "/OA_HTML/OA.jsp?page=profile&amp;selNo=228464",
            "https://selfservice.adb.org/OA_HTML/submit-application",
        )
        with self.assertRaises(MODULE.UnsafeRequest):
            MODULE.build_tab_submission(unsafe, URL, "lnk_tor")

    def test_rejects_application_submit_button(self):
        unsafe = PROFILE_HTML.replace(
            "_fwkActBtnName_lnk_tor_tab_select-token",
            "_fwkActBtnName_bEoi_Eoi-token",
        )
        with self.assertRaises(MODULE.UnsafeRequest):
            MODULE.build_tab_submission(unsafe, URL, "lnk_tor")

    def test_rejects_redirect_to_other_host(self):
        with self.assertRaises(MODULE.UnsafeRequest):
            MODULE.validate_adb_destination(
                "https://example.com/OA_HTML/OA.jsp",
                allowed_paths=MODULE.ALLOWED_RESPONSE_PATHS,
            )

    def test_allows_explicit_default_https_port_for_adb_redirect(self):
        destination = "https://selfservice.adb.org:443/OA_HTML/OA.jsp?selNo=228464"
        self.assertEqual(
            MODULE.validate_adb_destination(
                destination,
                allowed_paths=MODULE.ALLOWED_RESPONSE_PATHS,
            ),
            destination,
        )


class RetrievalTests(unittest.TestCase):
    def test_retries_incomplete_tor_once_and_returns_all_sections(self):
        calls = {"lnk_tor": 0, "lnk_cost": 0}

        def get_tab(url, tab_id):
            self.assertEqual(url, URL)
            calls[tab_id] += 1
            if tab_id == "lnk_tor" and calls[tab_id] == 1:
                return TOR_HTML.replace("<h2>Terms of Reference (Individual Consultant)</h2>", "")
            return TOR_HTML if tab_id == "lnk_tor" else COST_HTML

        result = MODULE.read_csrn(URL, profile_fetcher=lambda _: PROFILE_HTML, tab_fetcher=get_tab)
        self.assertTrue(result["ok"])
        self.assertEqual(result["retrieval"]["tor"]["attempts"], 2)
        self.assertEqual(result["retrieval"]["cost"]["status"], "ok")
        self.assertIn("Advanced economics degree", result["sections"]["minimum_qualifications"])
        self.assertIn("Diagnostic report", result["sections"]["deliverables"])
        self.assertIn("Home office, 20 days", result["sections"]["schedule"])
        self.assertIn("9,129", result["sections"]["cost_estimate"])

    def test_missing_cost_is_nonfatal(self):
        def get_tab(_, tab_id):
            if tab_id == "lnk_cost":
                raise MODULE.TabNotAvailable("record does not expose lnk_cost")
            return TOR_HTML

        result = MODULE.read_csrn(URL, profile_fetcher=lambda _: PROFILE_HTML, tab_fetcher=get_tab)
        self.assertTrue(result["ok"])
        self.assertEqual(result["retrieval"]["cost"]["status"], "not_available")

    def test_mismatched_tor_is_fatal_after_one_retry(self):
        mismatched = TOR_HTML.replace(TITLE, "Different assignment")
        calls = 0

        def get_tab(_, tab_id):
            nonlocal calls
            if tab_id == "lnk_tor":
                calls += 1
                return mismatched
            return COST_HTML

        result = MODULE.read_csrn(URL, profile_fetcher=lambda _: PROFILE_HTML, tab_fetcher=get_tab)
        self.assertFalse(result["ok"])
        self.assertEqual(calls, 2)
        self.assertEqual(result["retrieval"]["tor"]["status"], "error")
        self.assertIn("does not match", result["retrieval"]["tor"]["error"])

    def test_cli_exit_status_matches_top_level_ok(self):
        for expected_ok, expected_exit in ((True, 0), (False, 1)):
            with self.subTest(expected_ok=expected_ok):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_status = MODULE.main(
                        [URL],
                        reader=lambda _: {"ok": expected_ok},
                    )
                self.assertEqual(exit_status, expected_exit)
                self.assertEqual(json.loads(output.getvalue())["ok"], expected_ok)


if __name__ == "__main__":
    unittest.main()
