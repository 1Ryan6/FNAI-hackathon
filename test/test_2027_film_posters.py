"""
Unit and integration tests for the 2027 Film Concept Poster generation pipeline.
Validates the 5 major 2027 film profiles, concept poster motifs, and Imagen 3 rendered assets.
"""

import os
import unittest
from unittest.mock import patch

# Ensure test dir is on sys.path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_2027_film_poster import FILMS_2027, analyze_2027_films


class Test2027FilmPosters(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))

    def test_five_films_presence(self):
        """Verify all 5 anticipated 2027 films are fully defined."""
        expected_films = [
            "batman_arkham_descends",
            "superman_man_of_tomorrow",
            "minecraft_2",
            "sky_rat",
            "teenage_mutant_ninja_turtles_part_2"
        ]
        self.assertEqual(len(FILMS_2027), 5)
        for key in expected_films:
            self.assertIn(key, FILMS_2027, f"Missing 2027 film key: {key}")

    def test_film_poster_motifs_structure(self):
        """Verify each film profile includes complete concept poster design motifs."""
        required_motif_keys = ["palette", "focal_element", "lighting", "typography"]
        for key, film in FILMS_2027.items():
            self.assertIn("title", film)
            self.assertIn("studio", film)
            self.assertIn("premise", film)
            self.assertIn("concept_poster_motifs", film)
            self.assertIn("default_poster_prompt", film)

            motifs = film["concept_poster_motifs"]
            for m_key in required_motif_keys:
                self.assertIn(m_key, motifs, f"Film '{key}' missing motif '{m_key}'")

            # Check prompt mentions vertical ratio
            self.assertIn("Vertical 2:3", film["default_poster_prompt"])

    def test_analyze_2027_films_offline_fallback(self):
        """Verify analyze_2027_films produces complete fallback summary when offline."""
        with patch.dict(os.environ, {}, clear=True):
            summary = analyze_2027_films(api_key=None)
            self.assertIn("Batman", summary)
            self.assertIn("Superman", summary)
            self.assertIn("Minecraft", summary)
            self.assertIn("Sky Rat", summary)
            self.assertIn("Ninja Turtles", summary)

    def test_rendered_poster_assets_exist(self):
        """Verify that the Imagen 3 rendered poster assets are present in the test folder."""
        batman_poster = os.path.join(self.test_dir, "the_batman_2027_poster.jpg")
        superman_poster = os.path.join(self.test_dir, "superman_2027_poster.jpg")
        sky_rat_poster = os.path.join(self.test_dir, "sky_rat_2027_poster.jpg")

        self.assertTrue(os.path.exists(batman_poster), f"Missing {batman_poster}")
        self.assertTrue(os.path.exists(superman_poster), f"Missing {superman_poster}")
        self.assertTrue(os.path.exists(sky_rat_poster), f"Missing {sky_rat_poster}")

        # Ensure valid non-empty image files (> 100KB for 2:3 theatrical posters)
        self.assertGreater(os.path.getsize(batman_poster), 100_000)
        self.assertGreater(os.path.getsize(superman_poster), 100_000)
        self.assertGreater(os.path.getsize(sky_rat_poster), 100_000)


if __name__ == "__main__":
    unittest.main()
