"""M13 API persistence and provider-neutral context, without live model calls."""
import asyncio
import unittest
from unittest.mock import patch
import test_world_api as world
RecordingGenerator = world.RecordingGenerator
from app.guidance.service import build_context, suggest_next_scene
from app.guidance.schemas import SuggestionOptions
from app.guidance.generator import DeterministicSuggestionGenerator
from app.stories.metadata import creative_constraints
from app.story_import.schemas import ProposedStory
from pydantic import ValidationError


class StoryMetadataTests(unittest.TestCase):
    setUp = world.WorldAPITests.setUp
    tearDown = world.WorldAPITests.tearDown
    sign_in = world.WorldAPITests.sign_in
    post = world.WorldAPITests.post
    patch = world.WorldAPITests.patch

    def test_metadata_roundtrip_and_patch(self):
        created = self.post('/api/stories', dict(title='Cerita', language=' ID ', primary_genre='romance', secondary_genres=['drama']))
        root = '/api/stories/' + created['story_id']
        self.assertEqual(created['language'], 'id')
        self.assertEqual(self.client.get(root).json()['secondary_genres'], ['drama'])
        self.assertTrue(any(s['language'] == 'id' for s in self.client.get('/api/stories').json()))
        self.patch(root, {'language': 'JA'})
        self.patch(root, {'primary_genre': 'mystery'})
        changed = self.patch(root, {'secondary_genres': ['thriller']})
        self.assertEqual((changed['language'], changed['primary_genre'], changed['secondary_genres']), ('ja', 'mystery', ['thriller']))
        self.patch(root, {'primary_genre': 'thriller'}, expected=422)
        self.patch(root, {'secondary_genres': ['mystery']}, expected=422)
        self.assertEqual(self.client.get(root).json(), changed)
        self.patch(root, {'language': None, 'primary_genre': None, 'secondary_genres': []})
        self.assertIsNone(self.story['language'])
        self.assertIsNone(self.story['primary_genre'])
        self.assertEqual(self.story['secondary_genres'], [])

    def test_metadata_validation(self):
        for fields in [{'language': 'zz'}, {'language': 'English'}, {'language': 'x'*100},
                       {'primary_genre': 'made_up'}, {'secondary_genres': ['drama','drama']},
                       {'primary_genre': 'drama', 'secondary_genres': ['drama']},
                       {'secondary_genres': ['drama','comedy','romance','horror']}, {'secondary_genres': None}]:
            with self.subTest(fields=fields):
                self.post('/api/stories', {'title': 'Invalid', **fields}, expected=422)
                self.patch(self.root, fields, expected=422)

    def test_scene_context_authoritative_and_unchanged(self):
        self.patch(self.root, {'language': 'id', 'primary_genre': 'romance', 'secondary_genres': ['drama']})
        before = self.client.get(self.root).json()
        fake = RecordingGenerator('Ia kembali ke taman.')
        with patch('app.api.stories.get_story_generator', return_value=fake):
            self.post(self.root + '/scenes/generate', {'request': 'Continue in English'}, expected=200)
        ctx = fake.context
        self.assertEqual((ctx.language, ctx.primary_genre, ctx.secondary_genres), ('id','romance',['drama']))
        self.assertIn('Indonesian', ' '.join(creative_constraints(ctx.language, ctx.primary_genre, ctx.secondary_genres)))
        from app.stories.adapters.openai_generator import build_prompt
        prompt = build_prompt(ctx)
        self.assertIn('Indonesian (id)', prompt)
        self.assertIn('Genre is not Canon', prompt)
        self.assertIn('romance', prompt)
        self.assertEqual(self.client.get(self.root).json(), before)
        self.patch(self.root, {'language': None})
        with patch('app.api.stories.get_story_generator', return_value=fake):
            self.post(self.root + '/scenes/generate', {'request': 'Continue'}, expected=200)
        self.assertEqual(fake.context.language,"en")  # disclosed legacy fallback
        self.assertEqual(creative_constraints(None, None, []), ())

    def test_guidance_and_workflow_context(self):
        self.patch(self.root, {'language': 'id', 'primary_genre': 'romance', 'secondary_genres': ['drama']})
        before = self.client.get(self.root).json()
        with self.sessions() as db:
            ctx = build_context(db, self.story['story_id'], 'alice', SuggestionOptions(additional_instruction='Write in English'))
            self.assertEqual((ctx.language, ctx.primary_genre, ctx.secondary_genres), ('id','romance',['drama']))
            self.assertTrue(any('Indonesian' in rule for rule in ctx.constraints))
            result = asyncio.run(suggest_next_scene(db, self.story['story_id'], 'alice', SuggestionOptions(count=5), DeterministicSuggestionGenerator()))
            self.assertIn('Langkah', result.suggestions[0].title)
            self.assertIn('romance', result.suggestions[0].text)
            from app.workflows.service import perform_step
            from app.workflows.schemas import WorkflowAction
            class Capture(DeterministicSuggestionGenerator):
                async def suggest(inner, context, *, count):
                    self.assertEqual(context.language, 'id')
                    return await super().suggest(context, count=count)
            asyncio.run(perform_step(db, self.story['story_id'], 'alice', 'narrative_guidance', WorkflowAction(), generator=Capture(), extractor=None, planner=None))
        self.assertEqual(self.client.get(self.root).json(), before)

    def test_import_shared_vocabulary(self):
        proposal = ProposedStory(detected_language='zh-cn', primary_genre='romance', secondary_genres=['drama'], evidence=['source'])
        self.post('/api/stories', {'title': 'Reviewed', 'language': proposal.detected_language, 'primary_genre': proposal.primary_genre, 'secondary_genres': proposal.secondary_genres})
        with self.assertRaises(ValidationError):
            ProposedStory(detected_language='zz', primary_genre='drama', evidence=['source'])

    def test_supported_language_scaffolds_and_genre_limits(self):
        from app.stories.metadata import LANGUAGE_NAMES
        for language in LANGUAGE_NAMES:
            self.patch(self.root, {'language': language, 'primary_genre': 'romance', 'secondary_genres': ['drama']})
            with self.sessions() as db:
                result = asyncio.run(suggest_next_scene(db, self.story['story_id'], 'alice', SuggestionOptions(count=5), DeterministicSuggestionGenerator()))
                self.assertEqual(len(result.suggestions), 5)
                self.assertIn('romance', result.suggestions[0].text)
