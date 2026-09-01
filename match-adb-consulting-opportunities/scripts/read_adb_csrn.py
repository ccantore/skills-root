#!/usr/bin/env python3

"""Read an ADB Consulting Services Recruitment Notice without application actions."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)


ADB_SCHEME = "https"
ADB_HOST = "selfservice.adb.org"
RECORD_PATH = "/OA_HTML/adb/xxcrs/jsp/CsrnVw.jsp"
FORM_PATH = "/OA_HTML/OA.jsp"
ALLOWED_RESPONSE_PATHS = {RECORD_PATH, FORM_PATH}
USER_AGENT = "Mozilla/5.0 (compatible; Codex ADB opportunity reader/1.0)"
TIMEOUT_SECONDS = 25
MAX_RESPONSE_BYTES = 5 * 1024 * 1024

BLOCK_TAGS = {
    "br",
    "button",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "li",
    "p",
    "pre",
    "table",
    "td",
    "th",
    "tr",
}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
CAPTURE_IDS = {"mcConsultantType", "mcConsultantSource", "mstSelectionMethod"}

TAB_SPECS = {
    "lnk_tor": {
        "payload_key": "tab_tor",
        "button_marker": "lnk_tor_tab_select",
        "heading": "Terms of Reference (Individual Consultant)",
    },
    "lnk_cost": {
        "payload_key": "tab_cost",
        "button_marker": "lnk_cost_tab_select",
        "heading": "Cost Items",
    },
}


class CsrnError(RuntimeError):
    """Base error for safe CSRN retrieval."""


class InvalidRecordUrl(CsrnError):
    """The supplied record URL is outside the approved ADB endpoint."""


class UnsafeRequest(CsrnError):
    """A generated request violates the read-only request contract."""


class ParseError(CsrnError):
    """The ADB response did not contain the expected structure."""


class VerificationError(CsrnError):
    """The returned ADB content could not be tied to the requested record."""


class TabNotAvailable(CsrnError):
    """The record does not expose the requested tab."""


@dataclass(frozen=True)
class RecordUrl:
    canonical: str
    selection_id: str


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value).replace("\xa0", " ")).strip()


def validate_record_url(url: str) -> RecordUrl:
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    valid_query = len(query) == 1 and query[0][0] == "sel" and query[0][1].isdigit()
    if (
        parsed.scheme != ADB_SCHEME
        or parsed.netloc != ADB_HOST
        or parsed.path != RECORD_PATH
        or parsed.fragment
        or not valid_query
    ):
        raise InvalidRecordUrl(
            "expected https://selfservice.adb.org/OA_HTML/adb/xxcrs/jsp/"
            "CsrnVw.jsp?sel=<digits>"
        )
    selection_id = query[0][1]
    canonical = f"{ADB_SCHEME}://{ADB_HOST}{RECORD_PATH}?sel={selection_id}"
    if url != canonical:
        raise InvalidRecordUrl("record URL is not in canonical form")
    return RecordUrl(canonical=canonical, selection_id=selection_id)


def validate_adb_destination(url: str, *, allowed_paths: set[str]) -> str:
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise UnsafeRequest(f"refusing ADB request destination: {url}") from error
    if (
        parsed.scheme != ADB_SCHEME
        or parsed.hostname != ADB_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.path not in allowed_paths
        or parsed.fragment
    ):
        raise UnsafeRequest(f"refusing ADB request destination: {url}")
    return url


class SafeAdbRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination = urljoin(req.full_url, newurl)
        validate_adb_destination(destination, allowed_paths=ALLOWED_RESPONSE_PATHS)
        return super().redirect_request(req, fp, code, msg, headers, destination)


class CsrnHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.form_action: str | None = None
        self.form_depth = 0
        self.inputs: dict[str, str] = {}
        self.anchors: dict[str, str] = {}
        self.visible_chunks: list[str] = []
        self.skip_depth = 0
        self.title_depth = 0
        self.heading_stack: list[tuple[str, list[str]]] = []
        self.headings: list[str] = []
        self.active_capture_ids: list[str] = []
        self.capture_starts: list[tuple[str, str]] = []
        self.captured_text: dict[str, list[str]] = {key: [] for key in CAPTURE_IDS}

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if tag == "form":
            self.form_depth += 1
            if self.form_action is None:
                self.form_action = attributes.get("action") or None
        if self.form_depth and tag == "input" and attributes.get("name"):
            self.inputs[attributes["name"]] = attributes.get("value", "")
        if tag == "a" and attributes.get("id") in TAB_SPECS:
            self.anchors[attributes["id"]] = attributes.get("onclick", "")
        if tag == "title":
            self.title_depth += 1
        if tag in {"h1", "h2", "h3", "h4"}:
            self.heading_stack.append((tag, []))
        capture_id = attributes.get("id")
        if capture_id in CAPTURE_IDS and tag not in VOID_TAGS:
            self.active_capture_ids.append(capture_id)
            self.capture_starts.append((tag, capture_id))
        if not self.skip_depth and tag in BLOCK_TAGS:
            self.visible_chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if not self.skip_depth and tag in BLOCK_TAGS:
            self.visible_chunks.append("\n")
        if tag == "form" and self.form_depth:
            self.form_depth -= 1
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if self.heading_stack and self.heading_stack[-1][0] == tag:
            _, chunks = self.heading_stack.pop()
            heading = _normalize_space("".join(chunks))
            if heading:
                self.headings.append(heading)
        if self.capture_starts and self.capture_starts[-1][0] == tag:
            _, capture_id = self.capture_starts.pop()
            if capture_id in self.active_capture_ids:
                self.active_capture_ids.remove(capture_id)

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.visible_chunks.append(data)
        for _, chunks in self.heading_stack:
            chunks.append(data)
        for capture_id in self.active_capture_ids:
            self.captured_text[capture_id].append(data)

    @property
    def lines(self) -> list[str]:
        lines: list[str] = []
        for raw_line in "".join(self.visible_chunks).splitlines():
            line = _normalize_space(raw_line)
            if line and (not lines or line != lines[-1]):
                lines.append(line)
        return lines

    def text_for_id(self, element_id: str) -> str:
        return _normalize_space(" ".join(self.captured_text.get(element_id, [])))


def parse_html(source: str) -> CsrnHTMLParser:
    parser = CsrnHTMLParser()
    parser.feed(source)
    parser.close()
    return parser


def _find_heading(parser: CsrnHTMLParser, expected: str) -> bool:
    expected_normalized = _normalize_space(expected).casefold()
    return any(_normalize_space(item).casefold() == expected_normalized for item in parser.headings)


def _find_line_index(lines: list[str], heading: str, *, prefix: bool = False) -> int | None:
    expected = _normalize_space(heading).casefold()
    for index, line in enumerate(lines):
        candidate = _normalize_space(line).casefold()
        if candidate == expected or (prefix and candidate.startswith(expected)):
            return index
    return None


def extract_section(
    lines: list[str],
    heading: str,
    stop_headings: tuple[str, ...],
    *,
    prefix: bool = False,
) -> str:
    start = _find_line_index(lines, heading, prefix=prefix)
    if start is None:
        return ""
    output: list[str] = []
    stops = tuple(_normalize_space(item).casefold() for item in stop_headings)
    for line in lines[start:]:
        candidate = _normalize_space(line).casefold()
        if output and any(candidate == stop or candidate.startswith(stop) for stop in stops):
            break
        output.append(line)
    return "\n".join(output).strip()


def parse_profile(source: str) -> dict:
    parser = parse_html(source)
    title = next((heading for heading in parser.headings if heading), "")
    profile = extract_section(
        parser.lines,
        "Selection Profile",
        ("Export to PDF", "Back", "Copyright"),
    )
    combined = " ".join(parser.lines)
    dates = re.search(
        r"Date Published:\s*(.*?)\s+Deadline of Submitting EOI:\s*"
        r"(.*?Manila local time)",
        combined,
        re.IGNORECASE,
    )
    if not title or not profile:
        raise ParseError("profile response is missing its title or Selection Profile section")
    return {
        "title": title,
        "published_date": _normalize_space(dates.group(1)) if dates else None,
        "deadline": _normalize_space(dates.group(2)) if dates else None,
        "consultant_type": parser.text_for_id("mcConsultantType") or None,
        "source": parser.text_for_id("mcConsultantSource") or None,
        "selection_method": parser.text_for_id("mstSelectionMethod") or None,
        "profile": profile,
    }


def parse_tab_payload(onclick: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for object_body in re.findall(r"\{([^{}]*)\}", html.unescape(onclick)):
        payload.update(
            re.findall(
                r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]*)['\"]",
                object_body,
            )
        )
    return payload


def build_tab_submission(profile_source: str, record_url: str, tab_id: str) -> tuple[str, dict[str, str]]:
    validate_record_url(record_url)
    if tab_id not in TAB_SPECS:
        raise UnsafeRequest(f"unsupported ADB tab: {tab_id}")
    parser = parse_html(profile_source)
    if not parser.form_action:
        raise ParseError("profile response is missing the Oracle form action")
    if tab_id not in parser.anchors:
        raise TabNotAvailable(f"record does not expose {tab_id}")

    action = urljoin(record_url, html.unescape(parser.form_action))
    validate_adb_destination(action, allowed_paths={FORM_PATH})
    payload = dict(parser.inputs)
    payload.update(parse_tab_payload(parser.anchors[tab_id]))
    payload.update({"event": "tab_select", "source": "stlCsrn"})

    specification = TAB_SPECS[tab_id]
    if specification["payload_key"] not in payload:
        raise ParseError(f"{tab_id} payload is missing {specification['payload_key']}")
    if specification["button_marker"] not in payload.get("_FORM_SUBMIT_BUTTON", ""):
        raise UnsafeRequest(f"{tab_id} payload is not a verified tab-selection action")
    if payload.get("event") != "tab_select" or payload.get("source") != "stlCsrn":
        raise UnsafeRequest("refusing non-tab ADB form event")
    if payload.get("event") == "Eoi" or payload.get("source") == "bEoi":
        raise UnsafeRequest("refusing Express Interest form event")
    return action, payload


def _response_text(response) -> str:
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ParseError("ADB response exceeds the safe size limit")
    charset = "utf-8"
    headers = getattr(response, "headers", None)
    if headers is not None and hasattr(headers, "get_content_charset"):
        charset = headers.get_content_charset() or charset
    return raw.decode(charset, "replace")


def _make_opener():
    return build_opener(HTTPCookieProcessor(CookieJar()), SafeAdbRedirectHandler())


def _open_text(opener, request: Request) -> str:
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            validate_adb_destination(response.geturl(), allowed_paths=ALLOWED_RESPONSE_PATHS)
            return _response_text(response)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise CsrnError(f"ADB request failed: {error}") from error


def fetch_profile(record_url: str) -> str:
    validate_record_url(record_url)
    request = Request(record_url, headers={"User-Agent": USER_AGENT})
    return _open_text(_make_opener(), request)


def fetch_tab(record_url: str, tab_id: str) -> str:
    validate_record_url(record_url)
    opener = _make_opener()
    profile_request = Request(record_url, headers={"User-Agent": USER_AGENT})
    profile_source = _open_text(opener, profile_request)
    action, payload = build_tab_submission(profile_source, record_url, tab_id)
    body = urlencode(payload).encode("utf-8")
    tab_request = Request(
        action,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": record_url,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    return _open_text(opener, tab_request)


def _empty_result(record: RecordUrl) -> dict:
    return {
        "ok": False,
        "url": record.canonical,
        "selection_id": record.selection_id,
        "title": None,
        "published_date": None,
        "deadline": None,
        "consultant_type": None,
        "source": None,
        "selection_method": None,
        "sections": {
            "profile": "",
            "tor": "",
            "minimum_qualifications": "",
            "deliverables": "",
            "schedule": "",
            "cost_estimate": "",
        },
        "retrieval": {
            "profile": {"status": "error", "attempts": 0, "error": None},
            "tor": {"status": "error", "attempts": 0, "error": None},
            "cost": {"status": "error", "attempts": 0, "error": None},
        },
    }


def _verify_tab(source: str, expected_title: str, tab_id: str) -> CsrnHTMLParser:
    parser = parse_html(source)
    title = next((heading for heading in parser.headings if heading), "")
    if _normalize_space(title).casefold() != _normalize_space(expected_title).casefold():
        raise VerificationError(f"{tab_id} response title does not match the profile")
    expected_heading = TAB_SPECS[tab_id]["heading"]
    heading_present = _find_heading(parser, expected_heading)
    if tab_id == "lnk_cost":
        heading_present = heading_present or _find_line_index(parser.lines, expected_heading) is not None
    if not heading_present:
        raise VerificationError(f"{tab_id} response is missing the expected section heading")
    return parser


def read_csrn(
    url: str,
    *,
    profile_fetcher: Callable[[str], str] | None = None,
    tab_fetcher: Callable[[str, str], str] | None = None,
) -> dict:
    record = validate_record_url(url)
    result = _empty_result(record)
    get_profile = profile_fetcher or fetch_profile
    get_tab = tab_fetcher or fetch_tab

    try:
        profile_data = parse_profile(get_profile(record.canonical))
    except CsrnError as error:
        result["retrieval"]["profile"].update(attempts=1, error=str(error))
        result["retrieval"]["tor"].update(error="not attempted because profile verification failed")
        result["retrieval"]["cost"].update(error="not attempted because profile verification failed")
        return result

    result.update({key: profile_data[key] for key in (
        "title",
        "published_date",
        "deadline",
        "consultant_type",
        "source",
        "selection_method",
    )})
    result["sections"]["profile"] = profile_data["profile"]
    result["retrieval"]["profile"] = {"status": "ok", "attempts": 1, "error": None}

    for tab_id, retrieval_key in (("lnk_tor", "tor"), ("lnk_cost", "cost")):
        last_error: CsrnError | None = None
        parser: CsrnHTMLParser | None = None
        for attempt in (1, 2):
            try:
                source = get_tab(record.canonical, tab_id)
                parser = _verify_tab(source, profile_data["title"], tab_id)
                result["retrieval"][retrieval_key] = {
                    "status": "ok",
                    "attempts": attempt,
                    "error": None,
                }
                break
            except TabNotAvailable as error:
                last_error = error
                result["retrieval"][retrieval_key] = {
                    "status": "not_available" if tab_id == "lnk_cost" else "error",
                    "attempts": attempt,
                    "error": str(error),
                }
                break
            except CsrnError as error:
                last_error = error
        else:
            result["retrieval"][retrieval_key] = {
                "status": "error",
                "attempts": 2,
                "error": str(last_error) if last_error else "unknown retrieval error",
            }

        if parser is None:
            continue
        if tab_id == "lnk_tor":
            lines = parser.lines
            result["sections"]["tor"] = extract_section(
                lines,
                TAB_SPECS[tab_id]["heading"],
                ("Export to PDF", "Back", "Copyright"),
            )
            result["sections"]["minimum_qualifications"] = extract_section(
                lines,
                "Minimum Qualification Requirements",
                ("Deliverables", "Schedule and Places of Assignment", "Export to PDF", "Back", "Copyright"),
            )
            result["sections"]["deliverables"] = extract_section(
                lines,
                "Deliverables",
                ("Schedule and Places of Assignment", "Export to PDF", "Back", "Copyright"),
            )
            result["sections"]["schedule"] = extract_section(
                lines,
                "Schedule and Places of Assignment",
                ("Export to PDF", "Back", "Copyright"),
                prefix=True,
            )
        else:
            result["sections"]["cost_estimate"] = extract_section(
                parser.lines,
                TAB_SPECS[tab_id]["heading"],
                ("Export to PDF", "Back", "Copyright"),
            )

    result["ok"] = (
        result["retrieval"]["profile"]["status"] == "ok"
        and result["retrieval"]["tor"]["status"] == "ok"
    )
    return result


def _invalid_result(url: str, error: Exception) -> dict:
    return {
        "ok": False,
        "url": url,
        "selection_id": None,
        "title": None,
        "published_date": None,
        "deadline": None,
        "consultant_type": None,
        "source": None,
        "selection_method": None,
        "sections": {
            "profile": "",
            "tor": "",
            "minimum_qualifications": "",
            "deliverables": "",
            "schedule": "",
            "cost_estimate": "",
        },
        "retrieval": {
            "profile": {"status": "error", "attempts": 0, "error": str(error)},
            "tor": {"status": "error", "attempts": 0, "error": "not attempted"},
            "cost": {"status": "error", "attempts": 0, "error": "not attempted"},
        },
    }


def main(argv: list[str] | None = None, *, reader=None) -> int:
    argument_parser = argparse.ArgumentParser(
        description="Read an official ADB CSRN profile, TOR, and cost estimate as JSON."
    )
    argument_parser.add_argument("url", help="Canonical ADB CsrnVw.jsp?sel=<digits> URL")
    args = argument_parser.parse_args(argv)
    read_function = reader or read_csrn
    try:
        result = read_function(args.url)
    except CsrnError as error:
        result = _invalid_result(args.url, error)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
