import unittest

from scripts import audit_public_discoverability as audit


class PublicDiscoverabilityAuditTest(unittest.TestCase):
    def test_contract_is_read_without_importing_application(self):
        contract = audit.load_contract()
        paths = {page["path"] for page in contract["pages"]}
        self.assertTrue({"/robots.txt", "/sitemap.xml", "/llms.txt", "/llms-full.txt", "/", "/atlante", "/blog"} <= paths)
        self.assertTrue(any(path.startswith("/indicatore/") for path in paths))
        self.assertTrue(any(path.startswith("/regione/") for path in paths))
        self.assertTrue(any(path.startswith("/tema/") for path in paths))

    def test_robots_accepts_the_application_contract(self):
        contract = audit.load_contract()
        robots = contract["robots"]
        lines = ["# As a condition of accessing this website", "User-agent: *", "Allow: /"]
        lines += [f"Disallow: {path}" for path in robots["shared_disallow"]]
        lines += [f"User-agent: {agent}" for agent in robots["answer_bots"]]
        lines += ["Allow: /"] + [f"Disallow: {path}" for path in robots["shared_disallow"]]
        for agent in robots["training_bots"]:
            lines += [f"User-agent: {agent}", "Disallow: /"]
        self.assertEqual(audit.audit_robots("\n".join(lines), robots), [])

    def test_robots_rejects_a_second_cdn_default_group(self):
        contract = audit.load_contract()
        failures = audit.audit_robots(
            "# As a condition of accessing this website\nUser-agent: *\nAllow: /\n"
            "User-agent: *\nDisallow: /\n",
            contract["robots"],
        )
        self.assertTrue(any("exactly one default" in failure for failure in failures))

    def test_html_inspection_records_seo_and_server_rendering(self):
        contract = audit.load_contract()
        expected = next(page for page in contract["pages"] if page["path"] == "/")
        canonical = contract["site_url"] + "/"
        html = f'<html><head><link rel="canonical" href="{canonical}"><meta name="robots" content="{contract["index_header"]}"></head><body>{expected["marker"]}</body></html>'.encode()
        raw = {"url": canonical, "final_url": canonical, "status": 200, "headers": {"content-type": "text/html; charset=utf-8", "x-robots-tag": contract["index_header"]}, "body": html, "redirects": []}
        result = audit.inspect_result(raw, expected, contract)
        self.assertEqual(result["failures"], [])
        self.assertTrue(result["server_rendered"])
        self.assertEqual(result["response_bytes"], len(html))


if __name__ == "__main__":
    unittest.main()
