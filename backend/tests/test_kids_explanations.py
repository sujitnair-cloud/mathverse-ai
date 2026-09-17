"""Offline regression tests for presentation policy, not mathematical accuracy."""
import ast
import asyncio
import hashlib
import json
import time
from types import SimpleNamespace
from typing import Optional
from pathlib import Path
import unittest


# Load pure prompt helpers without API keys, provider calls, or database setup.
SOURCE = Path(__file__).resolve().parents[1] / 'app/services/llm_service.py'
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
nodes = [node for node in tree.body if (
    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    and node.name in {'_build_prompt', '_rich_fallback', '_get_topic_info',
                     'llm_full_solve', '_key_looks_real', '_ck', '_cache_get', '_cache_set',
                     '_extract_json_object', '_repair_json_backslashes', 'QuotaExhaustedError'}
) or isinstance(node, (ast.Assign, ast.AnnAssign))]
namespace = {'json': json, 'hashlib': hashlib, 'time': time, 'Optional': Optional}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), namespace)


class KidsExplanationTests(unittest.TestCase):
    def test_primary_examples_reach_provider_with_kids_policy(self):
        # Stub transport: verifies prompt plumbing, not generated answer quality.
        examples = [('3 + 2', '5'), ('14 - 6', '8'), ('4 * 3', '12'),
                    ('24 / 6', '4'), ('1/2 + 1/4', '3/4')]
        namespace['settings'] = SimpleNamespace(LLM_PROVIDER='openai', OPENAI_API_KEY='test-key-' * 4)
        namespace['_SOLVE_CACHE'].clear()
        for problem, answer in examples:
            async def provider(prompt, max_tokens):
                self.assertIn(problem, prompt)
                self.assertIn('one method', prompt)
                self.assertIn('under 90 words', prompt)
                self.assertIn('"common_mistakes": []', prompt)
                self.assertNotIn('540 km', prompt)
                return json.dumps({'answer': answer, 'steps': [], 'explanation': 'fixture'})
            namespace['_call_openai'] = provider
            with self.subTest(problem=problem):
                result = asyncio.run(namespace['llm_full_solve'](problem, 'kids'))
                self.assertEqual(result['answer'], answer)

    def test_kids_prompt_has_separate_short_policy(self):
        prompt = namespace['_build_prompt']('12 / 3', {'answer': '4'}, 'kids')
        self.assertIn('under 90 words', prompt)
        self.assertIn('one method', prompt)
        self.assertNotIn('Mention 1–2 common mistakes', prompt)

    def test_adult_prompt_keeps_existing_requirements(self):
        for level in ('intermediate', 'advanced'):
            prompt = namespace['_build_prompt']('12 / 3', {'answer': '4'}, level)
            self.assertIn('Mention 1–2 common mistakes', prompt)
            self.assertNotIn('under 90 words', prompt)

    def test_fallback_does_not_lecture_or_invent(self):
        text = namespace['_rich_fallback']('12 / 3', {'answer': '4'}, 'kids')
        self.assertIn('**Answer:** 4', text)
        self.assertIn('unavailable', text)
        self.assertNotIn('Essential Rules', text)
        self.assertLess(len(text.split()), 40)

    def test_missing_answer_is_not_presented_as_solved(self):
        text = namespace['_rich_fallback']('hard problem', {'answer': 'See steps'}, 'kids')
        self.assertIn("couldn't", text)
        self.assertNotIn('**Answer:**', text)


if __name__ == '__main__':
    unittest.main()
