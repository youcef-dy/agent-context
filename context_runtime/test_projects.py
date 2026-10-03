import unittest

from context_runtime.core import ContextAccessError, Principal
from context_runtime.projects import ObservedResource, Project, ProjectCatalog


STAMP = "2026-10-03T12:00:00Z"
OWNER = Principal("owner", frozenset({"owner", "company:alpha"}), "test-host")
OTHER = Principal("other", frozenset({"company:beta"}), "test-host")


class ProjectCatalogTests(unittest.TestCase):
    def test_confirmed_alias_resolves_with_review_provenance(self):
        project = Project("reg-affairs", "Regulatory Affairs", "owner",
                          ("RA",), "amine", STAMP)
        result = ProjectCatalog([project]).resolve(" ra ", "owner", OWNER)
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["project_id"], "reg-affairs")
        self.assertEqual(result["confirmed_by"], "amine")

    def test_render_observation_is_not_a_confirmed_project(self):
        service = ObservedResource("render", "srv-example", "Regulatory-Affairs", "owner", STAMP)
        result = ProjectCatalog([], [service]).resolve("Regulatory-Affairs", "owner", OWNER)
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["project_id"])
        self.assertEqual(result["observed_resource_labels"], ["Regulatory-Affairs"])

    def test_unrecognized_project_asks_without_guessing(self):
        result = ProjectCatalog([]).resolve("new client project", "owner", OWNER)
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["observed_resource_labels"], [])
        self.assertIn("source of truth", result["question"])

    def test_ambiguous_alias_does_not_pick_first(self):
        catalog = ProjectCatalog([
            Project("a", "Alpha", "owner", ("app",), "amine", STAMP),
            Project("b", "Beta", "owner", ("app",), "amine", STAMP),
        ])
        result = catalog.resolve("app", "owner", OWNER)
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["candidates"], ["Alpha", "Beta"])

    def test_wrong_scope_cannot_reveal_projects_or_observations(self):
        catalog = ProjectCatalog([], [ObservedResource(
            "render", "srv-private", "Secret", "owner", STAMP)])
        with self.assertRaises(ContextAccessError):
            catalog.resolve("Secret", "owner", OTHER)
        result = catalog.resolve("Secret", "company:beta", OTHER)
        self.assertEqual(result["observed_resource_labels"], [])

    def test_duplicate_identifiers_and_bad_names_rejected(self):
        project = Project("a", "Alpha", "owner", (), "amine", STAMP)
        with self.assertRaises(ValueError):
            ProjectCatalog([project, project])
        with self.assertRaises(ValueError):
            Project("x", " ", "owner", (), "amine", STAMP)


if __name__ == "__main__":
    unittest.main()
