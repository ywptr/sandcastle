"""Canon intelligence is owned by Sandcastle and requires no live model provider."""
import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from test_media import MediaFixture
from app.api.dependencies import get_db
from app.auth.identity import AuthenticatedIdentity
from app.auth.session import AuthSessionManager, SESSION_COOKIE
from app.canon import candidate_service as service
from app.canon.candidate_schemas import CandidateApproval, ManualCandidate
from app.canon.comparator import Comparison
from app.canon.deterministic_extractor import DeterministicCanonExtractor, get_canon_extractor
from app.canon.extractor import ExtractedCanonFact
from app.canon.service import create_canon_entry, update_canon_entry
from app.db.models import CanonCandidate, CanonEntry
from app.main import app
from app.media.errors import MediaDomainNotFound
from app.stories.scene_service import create_scene, update_scene
from app.stories.service import create_story
from app.world.service import create_character, create_place


class FakeExtractor:
    def __init__(self, facts):
        self.facts = facts

    async def extract(self, *, story_title, scene_content):
        return self.facts


class CanonFixture(MediaFixture):
    def propose(self, **changes):
        values = {"type": "character", "subject_id": self.character.character_id,
                  "fact_type": "physical_trait", "key": "eye_color", "value": "green", "evidence": "Manual proposal: green eyes"}
        return service.propose_candidate(self.db, story_id=self.story.story_id, user_id="alice", proposal=ManualCandidate(**(values | changes)))

    def add_canon(self, key="eye_color", value="green", **changes):
        return create_canon_entry(self.db, story_id=self.story.story_id, entry_type="character",
                                  key=key, value=value, subject_id=self.character.character_id, **changes)

    def approve(self, candidate, **changes):
        return service.approve_candidate(self.db, story_id=self.story.story_id, candidate_id=candidate.canon_candidate_id,
                                         user_id="alice", approval=CandidateApproval(**changes))


class CanonIntelligenceTests(CanonFixture):
    def test_default_extraction_resolves_ids_deduplicates_and_preserves_canon(self):
        update_scene(self.db, self.scene, content="Unit 7 has green eyes. Unit 7 is 35 years old. Unit 7 is alive.")
        before = self.db.scalar(select(func.count()).select_from(CanonEntry))
        with patch("socket.create_connection", side_effect=AssertionError("No provider networking")):
            rows = asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id,
                scene_id=self.scene.scene_id, user_id="alice", extractor=DeterministicCanonExtractor()))
        self.assertEqual({row.key for row in rows}, {"eye_color", "age", "alive"})
        self.assertTrue(all(row.subject_id == self.character.character_id for row in rows))
        self.assertTrue(all(row.status == "pending" and row.classification == "new" for row in rows))
        self.assertTrue(all(row.evidence in row.source_snapshot for row in rows))
        self.assertTrue(all(row.source_kind == "scene" and row.scene_id == self.scene.scene_id for row in rows))
        again = asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id,
            scene_id=self.scene.scene_id, user_id="alice", extractor=DeterministicCanonExtractor()))
        self.assertEqual([row.canon_candidate_id for row in rows], [row.canon_candidate_id for row in again])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(CanonEntry)), before)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(CanonCandidate)), 3)

    def test_four_classifications_are_separate_from_review_status(self):
        self.add_canon()
        consistent = self.propose(value="GREEN")
        conflict = self.propose(value="blue")
        new = self.propose(key="age", fact_type="age", value="35")
        uncertain = self.propose(key="capability", fact_type="capability", value="may fly", explicit=False)
        self.assertEqual([row.classification for row in [consistent, conflict, new, uncertain]],
                         ["consistent", "conflict", "new", "uncertain"])
        self.assertTrue(all(row.status == "pending" for row in [consistent, conflict, new, uncertain]))
        self.assertTrue(all(row.reasoning for row in [consistent, conflict, new, uncertain]))
        tentative = self.propose(key="ability", fact_type="capability", value="possibly fly")
        self.assertEqual(tentative.classification, "uncertain")
        self.assertEqual(conflict.comparison_snapshot[0]["value"], "green")

    def test_approval_conflict_replacement_is_explicit_and_history_is_preserved(self):
        original = self.add_canon()
        candidate = self.propose(value="blue")
        with self.assertRaises(service.CandidateConflict):
            self.approve(candidate)
        self.assertEqual(self.db.get(CanonEntry, original.canon_entry_id).status, "approved")
        approved = self.approve(candidate, replace_conflicts=True, note="Intentional continuity revision")
        self.assertEqual(approved.status, "approved")
        self.assertEqual(approved.classification, "conflict")
        self.assertIsNotNone(approved.reviewed_at)
        self.assertEqual(approved.superseded_entry_ids, [original.canon_entry_id])
        self.assertEqual(approved.comparison_snapshot[0]["value"], "green")
        self.assertEqual(self.db.get(CanonEntry, original.canon_entry_id).status, "superseded")
        self.assertEqual(self.db.get(CanonEntry, original.canon_entry_id).value, "green")
        replacement = self.db.get(CanonEntry, approved.approved_canon_entry_id)
        self.assertEqual(replacement.value, "blue")
        self.assertEqual(replacement.subject_id, self.character.character_id)
        count = self.db.scalar(select(func.count()).select_from(CanonEntry))
        self.approve(approved, replace_conflicts=True)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(CanonEntry)), count)
        with self.assertRaises(service.CandidateConflict):
            service.reject_candidate(self.db, story_id=self.story.story_id, candidate_id=approved.canon_candidate_id, user_id="alice")

    def test_consistent_approval_reuses_canon_and_rejection_never_mutates_it(self):
        original = self.add_canon(key="age", value="35")
        candidate = self.propose(key="age", value="35.0", fact_type="age")
        self.assertEqual(candidate.classification, "consistent")
        self.assertEqual(self.approve(candidate).approved_canon_entry_id, original.canon_entry_id)
        other = self.propose(key="age", value="36", fact_type="age")
        service.reject_candidate(self.db, story_id=self.story.story_id, candidate_id=other.canon_candidate_id,
                                 user_id="alice", note="Keep current age")
        self.assertEqual(other.status, "rejected")
        self.assertEqual(self.db.get(CanonEntry, original.canon_entry_id).value, "35")
        self.assertEqual(self.db.get(CanonEntry, original.canon_entry_id).status, "approved")
        with self.assertRaises(service.CandidateConflict):
            self.approve(other, replace_conflicts=True)

    def test_unknown_ambiguous_and_wrong_story_subjects_are_not_created(self):
        unknown = self.propose(subject_id=None, subject_name="Mara")
        self.assertEqual(unknown.classification, "uncertain")
        self.assertIsNone(unknown.subject_id)
        with self.assertRaises(service.CandidateConflict):
            self.approve(unknown, accept_uncertain=True)
        mara = create_character(self.db, self.story.story_id, name="Mara")
        approved = self.approve(unknown, subject_id=mara.character_id)
        self.assertEqual(approved.subject_id, mara.character_id)
        create_character(self.db, self.story.story_id, name="Mara")
        ambiguous = self.propose(subject_id=None, subject_name="Mara", key="age", value="35")
        self.assertEqual(ambiguous.classification, "uncertain")
        other_story = create_story(self.db, "alice", title="Other")
        other = create_character(self.db, other_story.story_id, name="Other")
        with self.assertRaises(MediaDomainNotFound):
            self.propose(subject_id=other.character_id)

    def test_reanalysis_and_review_see_later_canon_changes(self):
        candidate = self.propose()
        self.assertEqual(candidate.classification, "new")
        self.add_canon(value="blue")
        service.reclassify_pending(self.db, story_id=self.story.story_id, user_id="alice")
        self.assertEqual(candidate.classification, "conflict")
        with self.assertRaises(service.CandidateConflict):
            self.approve(candidate)
        self.assertEqual(self.db.get(CanonEntry, candidate.comparison_snapshot[0]["canon_entry_id"]).value, "blue")

    def test_approval_rechecks_without_explicit_reanalysis(self):
        candidate = self.propose()
        self.assertEqual(candidate.classification, "new")
        current = self.add_canon(value="blue")
        with self.assertRaises(service.CandidateConflict):
            self.approve(candidate)
        self.assertEqual(self.db.get(CanonEntry, current.canon_entry_id).status, "approved")
        approved = self.approve(candidate, replace_conflicts=True)
        self.assertEqual(approved.classification, "conflict")
        self.assertEqual(approved.superseded_entry_ids, [current.canon_entry_id])

    def test_normalized_manual_dedup_and_structured_fact_families(self):
        self.assertEqual(ExtractedCanonFact(type="world", key="location", value="north", evidence="north").key, "location")
        first = self.propose(key="Eye Color", value="GREEN")
        second = self.propose(key="eye_color", value="green")
        self.assertEqual(first.canon_candidate_id, second.canon_candidate_id)
        update_scene(self.db, self.scene, content="Unit 7 is gentle. Unit 7 owns a silver key. Unit 7 can fly. Unit 7 is married to Mara.")
        rows = asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                                     user_id="alice", extractor=DeterministicCanonExtractor()))
        self.assertEqual({row.fact_type for row in rows}, {"personality", "possession", "capability", "relationship"})

    def test_changed_scene_is_stale_and_bad_structured_output_is_atomic(self):
        update_scene(self.db, self.scene, content="Unit 7 has green eyes.")
        rows = asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                                     user_id="alice", extractor=DeterministicCanonExtractor()))
        update_scene(self.db, self.scene, content="Unit 7 has blue eyes.")
        service.reclassify_pending(self.db, story_id=self.story.story_id, user_id="alice")
        self.assertEqual(rows[0].classification, "uncertain")
        with self.assertRaises(service.CandidateConflict):
            self.approve(rows[0], accept_uncertain=True)
        count = self.db.scalar(select(func.count()).select_from(CanonCandidate))
        for facts in ["invalid prose", [{"type": "character", "key": "age", "value": "35"}],
                      [ExtractedCanonFact(type="world", key="rule", value="invented", evidence="Not in source")]]:
            with self.subTest(facts=facts), self.assertRaises(service.ExtractionFailed):
                asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id, scene_id=self.scene.scene_id,
                                                       user_id="alice", extractor=FakeExtractor(facts)))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(CanonCandidate)), count)

    def test_unstructured_comparison_is_conservative_and_optional_semantics_is_injected(self):
        self.add_canon(key="role", value="Guardian of the city")
        candidate = self.propose(key="role", fact_type="role", value="City protector")
        self.assertEqual(candidate.classification, "uncertain")
        class Equivalent:
            def compare(self, candidate, approved_facts):
                return Comparison("consistent", "Human-supplied semantic comparator considers these equivalent")
        service.reclassify_pending(self.db, story_id=self.story.story_id, user_id="alice", semantic=Equivalent())
        self.assertEqual(candidate.classification, "consistent")
        # Review rechecks without assuming an optional adjudicator remains configured.
        with self.assertRaises(service.CandidateConflict):
            self.approve(candidate)
        approved = self.approve(candidate, accept_uncertain=True, replace_conflicts=True)
        self.assertEqual(approved.status, "approved")

    def test_legacy_subject_keys_and_unscoped_canon_are_handled_safely(self):
        create_canon_entry(self.db, story_id=self.story.story_id, entry_type="character",
                           key="character.unit_7.eye_color", value="green")
        candidate = self.propose(value="blue")
        self.assertEqual(candidate.classification, "conflict")
        create_canon_entry(self.db, story_id=self.story.story_id, entry_type="character", key="age", value="35")
        ambiguous = self.propose(key="age", value="36", fact_type="age")
        self.assertEqual(ambiguous.classification, "uncertain")

    def test_story_place_and_labeled_world_extraction_report_and_reviewed_dedup(self):
        place = create_place(self.db, self.story.story_id, name="Old Harbor")
        self.story.premise = "Old Harbor has a cold climate. Rule resurrection: magic cannot revive the dead. Event evacuation: citizens left at dawn."
        self.db.commit()
        rows = asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id, user_id="alice", extractor=DeterministicCanonExtractor()))
        self.assertEqual({row.type for row in rows}, {"place", "world", "event"})
        self.assertEqual(next(row for row in rows if row.type == "place").subject_id, place.place_id)
        self.assertTrue(all(row.scene_id is None and row.source_kind == "story" for row in rows))
        service.reject_candidate(self.db, story_id=self.story.story_id, candidate_id=rows[0].canon_candidate_id, user_id="alice")
        again = asyncio.run(service.extract_candidates(self.db, story_id=self.story.story_id, user_id="alice", extractor=DeterministicCanonExtractor()))
        self.assertEqual(len(again), 3)
        self.assertEqual(rows[0].status, "rejected")
        report = service.continuity_report(self.db, story_id=self.story.story_id, user_id="alice")
        self.assertEqual(report.total, 2)
        self.assertEqual(report.counts["new"], 2)
        self.assertEqual(sum(report.counts.values()), 2)


class CanonIntelligenceAPITests(CanonFixture):
    def setUp(self):
        super().setUp()
        def override_db():
            with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.sign_in("alice")
        self.root = f"/api/stories/{self.story.story_id}/canon"

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        super().tearDown()

    def sign_in(self, user):
        token = AuthSessionManager(os.environ["SANDCASTLE_AUTH_SECRET"]).create_session_token(AuthenticatedIdentity(user, f"{user}@example.test", user))
        self.client.cookies.set(SESSION_COOKIE, token)

    def test_extract_list_filter_read_approve_reject_and_report(self):
        update_scene(self.db, self.scene, content="Unit 7 has green eyes. Unit 7 is 35 years old.")
        url = f"/api/stories/{self.story.story_id}/scenes/{self.scene.scene_id}/canon/candidates/extract"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()
        self.assertEqual(len(rows), 2)
        candidate_id = rows[0]["canon_candidate_id"]
        self.assertEqual(self.client.get(self.root + "/candidates?status=pending&classification=new").status_code, 200)
        self.assertEqual(self.client.get(self.root + f"/candidates/{candidate_id}").status_code, 200)
        approved = self.client.post(self.root + f"/candidates/{candidate_id}/approve", json={})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "approved")
        rejected = self.client.post(self.root + f"/candidates/{rows[1]['canon_candidate_id']}/reject", json={"note": "Not established yet"})
        self.assertEqual(rejected.json()["status"], "rejected")
        self.assertEqual(self.client.get(self.root + "/continuity").json()["total"], 0)
        self.assertEqual(self.client.post(self.root + "/candidates/reclassify").status_code, 200)
        self.assertEqual(self.client.get(self.root + "/candidates?status=invalid").status_code, 422)

    def test_manual_conflict_and_subject_scope_validation(self):
        existing = self.client.post(self.root, json={"type": "character", "subject_id": self.character.character_id,
                                                    "key": "eye_color", "value": "green"})
        self.assertEqual(existing.status_code, 201, existing.text)
        body = {"type": "character", "subject_id": self.character.character_id, "fact_type": "physical_trait",
                "key": "eye_color", "value": "blue", "evidence": "Author explicitly proposes blue eyes"}
        response = self.client.post(self.root + "/candidates", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["source_kind"], "manual")
        candidate_id = response.json()["canon_candidate_id"]
        self.assertEqual(self.client.post(self.root + f"/candidates/{candidate_id}/approve").status_code, 409)
        approved = self.client.post(self.root + f"/candidates/{candidate_id}/approve", json={"replace_conflicts": True})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(self.client.post(self.root, json={"type": "character", "subject_id": "missing", "key": "age", "value": "35"}).status_code, 404)

    def test_ownership_missing_resources_and_fake_extractor_boundary(self):
        update_scene(self.db, self.scene, content="Unit 7 has green eyes.")
        app.dependency_overrides[get_canon_extractor] = lambda: FakeExtractor([
            {"type": "character", "subject_id": self.character.character_id, "key": "eye_color", "value": "green", "evidence": self.scene.content}])
        url = f"/api/stories/{self.story.story_id}/scenes/{self.scene.scene_id}/canon/candidates/extract"
        result = self.client.post(url)
        self.assertEqual(result.status_code, 200, result.text)
        cid = result.json()[0]["canon_candidate_id"]
        self.assertEqual(self.client.get(self.root + "/candidates?scene_id=missing").status_code, 404)
        self.assertEqual(self.client.post(url.replace(self.scene.scene_id, "missing")).status_code, 404)
        own_other_story = create_story(self.db, "alice", title="Other owned story")
        self.assertEqual(self.client.get(f"/api/stories/{own_other_story.story_id}/canon/candidates/{cid}").status_code, 404)
        self.assertEqual(self.client.post(url.replace(self.story.story_id, own_other_story.story_id)).status_code, 404)
        self.sign_in("bob")
        for path in [self.root + "/candidates", self.root + f"/candidates/{cid}", self.root + "/continuity"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        for path in [url, self.root + "/candidates/reclassify", self.root + f"/candidates/{cid}/approve", self.root + f"/candidates/{cid}/reject"]:
            self.assertEqual(self.client.post(path).status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.root + "/candidates").status_code, 401)
