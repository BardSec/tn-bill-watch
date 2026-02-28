"""
LegiScan API client wrapper.
API base: https://api.legiscan.com/
All operations are GET requests with ?key=KEY&op=OPERATION&...
"""

import time
import requests


class LegiScanError(Exception):
    pass


class LegiScanClient:
    BASE_URL = "https://api.legiscan.com/"

    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()

    def _request(self, op, params=None, retries=3):
        if params is None:
            params = {}
        params["key"] = self.api_key
        params["op"] = op

        for attempt in range(retries):
            try:
                resp = self.session.get(self.BASE_URL, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "OK":
                    return data
                raise LegiScanError(f"API returned error for op={op}: {data}")
            except requests.RequestException as exc:
                if attempt == retries - 1:
                    raise LegiScanError(
                        f"Request failed after {retries} attempts: {exc}"
                    ) from exc
                time.sleep(2 ** attempt)

    def get_session_list(self, state="TN"):
        """Return all legislative sessions for the given state."""
        data = self._request("getSessionList", {"state": state})
        sessions = data["sessions"]
        # API may return a dict keyed by index or a list
        if isinstance(sessions, dict):
            sessions = list(sessions.values())
        return sessions

    def get_current_session(self, state="TN"):
        """Return the most recent active (or latest) session for the state."""
        sessions = self.get_session_list(state)
        active = [s for s in sessions if not s.get("sine_die", 1)]
        pool = active if active else sessions
        return max(pool, key=lambda s: s.get("year_start", 0))

    def get_master_list(self, session_id):
        """
        Return a list of bill summaries for the given session.
        Each summary includes: bill_id, number, change_hash, status,
        last_action, last_action_date, url, title, description.
        """
        data = self._request("getMasterList", {"id": session_id})
        master = data["masterlist"]
        # Key '0' holds session metadata, not a bill
        master.pop("0", None)
        return list(master.values())

    def get_bill(self, bill_id):
        """Return full bill detail including sponsors, subjects, history, texts."""
        data = self._request("getBill", {"id": bill_id})
        return data["bill"]

    def search(self, query, state="TN", page=1):
        """
        Full-text search across legislation.
        Returns up to 50 results per page in searchresult.results.
        """
        data = self._request("search", {"state": state, "query": query, "page": page})
        return data["searchresult"]
