"""
Unit and integration tests for the Meme Reanimation demonstration pipeline.
Tests visual prompt synthesis with Gemini 2.5 Flash and Imagen 3 execution.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure the test directory is on sys.path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reanimate_meme import (
    MEME_PROFILES,
    build_gemini_prompt,
    synthesize_visual_description,
    browse_recent_memes,
    generate_with_imagen,
)


class TestMemeReanimation(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))

    def test_meme_profiles_structure(self):
        """Verify each meme profile has essential fields for Imagen 3 rendering."""
        required_keys = ["title", "origin", "cultural_vibe", "visual_features", "default_synthesized_prompt"]
        for key, profile in MEME_PROFILES.items():
            for req in required_keys:
                self.assertIn(req, profile, f"Profile '{key}' missing required key '{req}'")
            
            # Check visual features granularity
            features = profile["visual_features"]
            self.assertIn("subject", features)
            self.assertIn("art_style", features)
            self.assertTrue(len(profile["default_synthesized_prompt"]) > 100)

    def test_build_gemini_prompt(self):
        """Verify instruction construction for Gemini 2.5 Flash."""
        chill_guy = MEME_PROFILES["chill_guy"]
        prompt = build_gemini_prompt(chill_guy)
        self.assertIn("Chill Guy", prompt)
        self.assertIn("Imagen 3", prompt)
        self.assertIn("3D animated", prompt)

    def test_synthesize_visual_description_fallback(self):
        """Verify graceful fallback to high-fidelity prompt when offline or no API key."""
        with patch.dict(os.environ, {}, clear=True):
            prompt = synthesize_visual_description("chill_guy", api_key=None)
            self.assertEqual(prompt, MEME_PROFILES["chill_guy"]["default_synthesized_prompt"])
            self.assertIn("Chill Guy", prompt)
            self.assertIn("grey knit crewneck sweater", prompt)
            self.assertIn("red canvas", prompt)

    def test_synthesize_visual_description_invalid_meme(self):
        """Verify ValueError raised for unknown meme."""
        with self.assertRaises(ValueError):
            synthesize_visual_description("non_existent_meme_xyz")

    @patch("google.genai.Client")
    def test_synthesize_visual_description_with_gemini_mock(self, mock_client_cls):
        """Verify Gemini 2.5 Flash client invocation when API key is provided."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "A photorealistic 3D render of Chill Guy standing with relaxed hands in pockets."
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = synthesize_visual_description(
            "chill_guy",
            api_key="mock-api-key",
            model_name="gemini-2.5-flash"
        )
        self.assertEqual(result, "A photorealistic 3D render of Chill Guy standing with relaxed hands in pockets.")
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args[1]
        self.assertEqual(call_kwargs["model"], "gemini-2.5-flash")

    def test_generate_with_imagen_dry_run(self):
        """Verify Imagen 3 dry run behavior without API key."""
        with patch.dict(os.environ, {}, clear=True):
            success = generate_with_imagen(
                prompt="Test prompt",
                output_path=os.path.join(self.test_dir, "test_output.jpg"),
                api_key=None
            )
            self.assertFalse(success)

    @patch("google.genai.Client")
    def test_generate_with_imagen_mock(self, mock_client_cls):
        """Verify Imagen 3 API invocation and file output with mock client."""
        mock_client = MagicMock()
        mock_image_item = MagicMock()
        mock_image_item.image.image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # JPEG header bytes
        mock_result = MagicMock()
        mock_result.generated_images = [mock_image_item]
        mock_client.models.generate_images.return_value = mock_result
        mock_client_cls.return_value = mock_client

        output_path = os.path.join(self.test_dir, "mock_output.jpg")
        try:
            success = generate_with_imagen(
                prompt="3D Chill Guy in cozy sweater",
                output_path=output_path,
                api_key="mock-api-key",
                model_name="imagen-3.0-generate-002"
            )
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "rb") as f:
                content = f.read()
                self.assertEqual(content, b"\xff\xd8\xff\xe0\x00\x10JFIF")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_browse_recent_memes_offline(self):
        """Verify browse_recent_memes returns baseline summaries when offline."""
        with patch.dict(os.environ, {}, clear=True):
            result = browse_recent_memes(api_key=None)
            self.assertIn("Chill Guy", result)
            self.assertIn("Moo Deng", result)
            self.assertIn("Yusuf Dikeç", result)

    def test_reanimated_assets_exist(self):
        """Verify that the generated Imagen 3 reanimated assets are present in the test directory."""
        chill_guy_path = os.path.join(self.test_dir, "chill_guy_reanimated.jpg")
        moo_deng_path = os.path.join(self.test_dir, "moo_deng_reanimated.jpg")
        yusuf_dikec_path = os.path.join(self.test_dir, "yusuf_dikec_reanimated.jpg")

        self.assertTrue(os.path.exists(chill_guy_path), f"Missing {chill_guy_path}")
        self.assertTrue(os.path.exists(moo_deng_path), f"Missing {moo_deng_path}")
        self.assertTrue(os.path.exists(yusuf_dikec_path), f"Missing {yusuf_dikec_path}")

        # Check file sizes (> 50KB to ensure valid image data)
        self.assertGreater(os.path.getsize(chill_guy_path), 50_000)
        self.assertGreater(os.path.getsize(moo_deng_path), 50_000)
        self.assertGreater(os.path.getsize(yusuf_dikec_path), 50_000)


if __name__ == "__main__":
    unittest.main()
