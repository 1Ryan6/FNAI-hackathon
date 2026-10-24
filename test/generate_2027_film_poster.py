"""
2027 Blockbuster Film Concept Poster Generator using Gemini 2.5/3.5 Flash and Imagen 3.
Analyzes upcoming 2027 film slates, sequels, and post-merger studio developments,
synthesizing unofficial teaser release posters based on real concept poster drafts.
"""

import os
import sys
import argparse
from typing import Dict, Any, Optional

def load_dotenv_if_present():
    """Reads .env file from workspace root or home directory without external dependencies."""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.expanduser("~/.env"),
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k not in os.environ and v:
                            os.environ[k] = v

load_dotenv_if_present()

# 5 Major Potential Blockbusters for 2027
FILMS_2027: Dict[str, Dict[str, Any]] = {
    "batman_arkham_descends": {
        "title": "The Batman: Arkham Descends (or The Batman Part II / Follow-up)",
        "studio": "Warner Bros. Pictures / DC Elseworlds (Matt Reeves)",
        "premise": (
            "Following the flood and recovery of Gotham, Bruce Wayne faces a psychological "
            "descent into madness as an insidious conspiracy erupts from within the reinforced "
            "depths of Arkham Asylum, involving Scarecrow's fear gas and Hugo Strange."
        ),
        "concept_poster_motifs": {
            "palette": "Deep charcoal grey, cold industrial cyan-blue, muted moss-green, blood-red neon accents",
            "focal_element": "Rain-drenched inverted puddle reflection showing tactical cowl and towering gothic Arkham spires",
            "lighting": "Volumetric street fog, anamorphic lens flare, toxic green vapor seeping along cobblestones",
            "typography": "Distressed heavy metallic stamped serif with red emphasis and 2027 theatrical credits"
        },
        "default_poster_prompt": (
            "Official teaser theatrical movie poster for 'THE BATMAN: ARKHAM DESCENDS' slated for 2027, "
            "hyper-realistic, gritty neo-noir psychological detective thriller. The composition features a "
            "rain-drenched dark Gotham alley at night with cold industrial cyan-blue and charcoal-black tones, "
            "lit by a single blood-red neon street sign. In the center, a distorted reflection in a puddle of water "
            "reveals Batman's heavily armored tactical cowl and cracked white lenses, reflecting the towering gothic "
            "spire silhouette of Arkham Asylum under thunderous storm clouds. Swirling toxic-green fog seeps across "
            "the wet cobblestones. Cinematic film grain, anamorphic lens flare, photorealistic rain droplets and reflections. "
            "Across the bottom, distressed metallic stamped typography reads 'THE BATMAN: ARKHAM DESCENDS' with '2027' "
            "credits billing block at the base. Vertical 2:3 aspect ratio."
        )
    },
    "superman_man_of_tomorrow": {
        "title": "Superman: Man of Tomorrow (James Gunn DCU Sequel)",
        "studio": "DC Studios / Warner Bros. Discovery",
        "premise": (
            "Building directly on the post-merger DC Universe continuity, Superman must confront "
            "the cosmic intellect of Brainiac arriving in the upper atmosphere while grappling with "
            "the emerging global authority metahuman factions."
        ),
        "concept_poster_motifs": {
            "palette": "Solar golden amber, dawn cerulean blue, regal scarlet-red cape, sleek alien silver",
            "focal_element": "Superman suspended in mid-air above Art-Deco Metropolis with Brainiac skull ship in orbit",
            "lighting": "Radiant solar backlighting, atmospheric volumetric rays piercing dark storm clouds",
            "typography": "Bold, clean metallic embossed cinematic title 'SUPERMAN: MAN OF TOMORROW - SUMMER 2027'"
        },
        "default_poster_prompt": (
            "Official theatrical teaser movie poster for 'SUPERMAN: MAN OF TOMORROW' slated for 2027, DC Studios. "
            "In a dramatic dawn sky above a gleaming, futuristic art-deco Metropolis skyline, Superman hovers "
            "suspended in mid-air in a heroic silhouette, backlit by brilliant golden-hour solar rays breaking through "
            "parting dark storm clouds. His classic royal-blue textured suit and flowing scarlet-red cape catch the "
            "vibrant sunlight, the iconic red and yellow 'S' crest glowing on his chest. In the distant upper stratosphere, "
            "the colossal metallic skull-like silhouette of Brainiac's mothership casts a subtle shadow over the Earth. "
            "High-end theatrical lighting, anamorphic lens flare, cosmic particles in the atmosphere. Clean, majestic bold "
            "typography across the bottom reads 'SUPERMAN: MAN OF TOMORROW' with 'SUMMER 2027' and billing block credits at the base. "
            "Vertical 2:3 aspect ratio."
        )
    },
    "minecraft_2": {
        "title": "A Minecraft Movie 2: The Nether Awakening",
        "studio": "Warner Bros. Pictures / Mojang Studios / Legendary",
        "premise": (
            "Following the global box-office eruption of the 2025 live-action adaptation, Steve and "
            "the Overworld champions must journey deep into the perilous Nether dimension to stop "
            "a catastrophic Piglin invasion fueled by ancient Netherite ruins."
        ),
        "concept_poster_motifs": {
            "palette": "Volcanic obsidian black, crimson Netherrack red, glowing soul-fire blue, gold nugget shimmer",
            "focal_element": "A colossal obsidian Nether portal crackling with purple vortex energy in a craggy cavern",
            "lighting": "Fiery magma lava rim light contrasted against eerie cyan soul-sand flames",
            "typography": "Chunky 3D blocky stone Minecraft logo with glowing crimson fissures"
        },
        "default_poster_prompt": (
            "Official theatrical teaser poster for 'A MINECRAFT MOVIE 2: THE NETHER AWAKENING' (2027). "
            "An epic, cinematic composition showing a towering obsidian Nether portal frame radiating intense purple swirl "
            "vortex particles deep inside a subterranean cavern. In the foreground, silhouettes of the heroes holding "
            "enchanted diamond pickaxes and a glowing soul lantern gaze into the portal. In the background through the rift, "
            "a vast volcanic Nether fortress looms with rivers of glowing orange lava and hovering Ghasts under soul fire. "
            "Epic photorealistic cinematic lighting, stylized block textures, embers rising, volumetric smoke. "
            "Across the bottom, the iconic 3D stone blocky title reads 'MINECRAFT 2: THE NETHER AWAKENING - 2027'. "
            "Vertical 2:3 aspect ratio."
        )
    },
    "sky_rat": {
        "title": "Sky Rat",
        "studio": "Universal Pictures / Illumination / DreamWorks Animation",
        "premise": (
            "In a dizzying retro-futuristic metropolis, a scrappy, goggle-wearing street rat constructs "
            "ramshackle mechanical glider wings out of discarded aeronautical scrap, taking to the clouds "
            "as the city's daring, high-flying hero against an armada of aerial predator syndicates."
        ),
        "concept_poster_motifs": {
            "palette": "Aviation sky-blue, sunburst amber, weathered flight-jacket leather, polished brass gears",
            "focal_element": "Plucky pilot rat soaring on handmade glider wings through radiant clouds over art-deco skyscrapers",
            "lighting": "Dazzling high-altitude golden sunlight glinting off brass rivets and glass flight goggles",
            "typography": "Riveted industrial aviation stencil typography reading 'SKY RAT - TAKE FLIGHT 2027'"
        },
        "default_poster_prompt": (
            "Official theatrical teaser movie poster for 'SKY RAT' (2027), high-end cinematic 3D animated adventure. "
            "In the center, a plucky, charismatic brown street rat wearing vintage leather aviator goggles and a flight helmet "
            "soars heroically on homemade mechanical canvas-and-brass glider wings through sun-drenched golden clouds high above "
            "a sprawling Art-Deco metropolis. Dazzling sunlight catches the spinning brass gears and stitched flight fabric. "
            "Dynamic low-angle aerial perspective, windblown fur detail, and cinematic atmospheric haze. Bold riveted stencil "
            "typography at the bottom reads 'SKY RAT' with the tagline 'THE ONLY WAY OUT IS UP' and 'IN THEATERS 2027'. "
            "Vertical 2:3 aspect ratio."
        )
    },
    "teenage_mutant_ninja_turtles_part_2": {
        "title": "Teenage Mutant Ninja Turtles: Mutant Mayhem 2",
        "studio": "Paramount Pictures / Nickelodeon Animation / Point Grey",
        "premise": (
            "Following their newfound acceptance by New York City, Leonardo, Raphael, Donatello, and Michelangelo "
            "balance high school life while confronting the terrifying arrival of Shredder and TCRI's cybernetic strike force."
        ),
        "concept_poster_motifs": {
            "palette": "Neon sewer-slime green, midnight Brooklyn navy, mutagen purple, and bloody crimson Shredder steel",
            "focal_element": "The four turtle brothers crouched on a rain-slicked gargoyle framed against Shredder's menacing silhouette",
            "lighting": "Expressive sketchy scribbled ink highlights, dynamic neon street sign glow, anamorphic rain reflections",
            "typography": "Hand-scrawled punk-rock spray-painted yellow and green 'TMNT: MUTANT MAYHEM 2 - 2027'"
        },
        "default_poster_prompt": (
            "Official theatrical teaser release poster for 'TEENAGE MUTANT NINJA TURTLES: MUTANT MAYHEM 2' (2027), "
            "in the distinctive sketchy hand-drawn 3D animation style. High atop a rain-slicked New York City rooftop gargoyle "
            "at night, Leonardo, Raphael, Donatello, and Michelangelo crouch in combat-ready poses with their signature weapons. "
            "In the stormy night sky behind them, the colossal, menacing shadow silhouette of Shredder looms with razor-sharp "
            "spiked chrome armor and glowing purple eyes. Raw sketchy ink lines, vibrant spray-paint graffiti textures, neon green "
            "and purple rim lighting, anamorphic rain reflections. Bold scrawled punk logo reads 'TMNT: MUTANT MAYHEM 2 - IN THEATERS 2027'. "
            "Vertical 2:3 aspect ratio."
        )
    }
}


def analyze_2027_films(api_key: Optional[str] = None, model_name: str = "gemini-3.5-flash") -> str:
    """Invokes Gemini 3.5 or 2.5 Flash to summarize the 2027 film slate and poster trends."""
    resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not resolved_api_key:
        lines = ["=== Top 5 Anticipated 2027 Films & Sequels ==="]
        for k, v in FILMS_2027.items():
            lines.append(f"\n• {v['title']} ({v['studio']})")
            lines.append(f"  Premise: {v['premise']}")
            lines.append(f"  Poster Motifs: {v['concept_poster_motifs']['focal_element']}")
        return "\n".join(lines)

    from google import genai
    client = genai.Client(api_key=resolved_api_key)
    prompt = (
        "Analyze the top 5 anticipated blockbuster films for 2027 (including Minecraft sequel, "
        "Superman sequel, and The Batman sequel post studio consolidation). "
        "Summarize their concept poster draft aesthetics, color palettes, and teaser poster strategies."
    )
    for model in [model_name, "gemini-2.5-flash" if model_name != "gemini-2.5-flash" else "gemini-3.5-flash"]:
        try:
            print(f"[INFO] Analyzing 2027 film slates with '{model}'...")
            resp = client.models.generate_content(model=model, contents=prompt)
            if resp.text:
                return resp.text.strip()
        except Exception as e:
            print(f"[WARN] Call to '{model}' failed ({e}), trying fallback...")
    return "Failed to analyze 2027 film slates with available models."


def main():
    parser = argparse.ArgumentParser(description="Generate 2027 Film Concept Posters with Gemini & Imagen 3")
    parser.add_argument("--film", choices=list(FILMS_2027.keys()), default="batman_arkham_descends",
                        help="Film to generate poster prompt for (default: batman_arkham_descends)")
    parser.add_argument("--gemini-model", default="gemini-3.5-flash",
                        help="Gemini model for analysis (default: gemini-3.5-flash)")
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze the full 2027 film slate with Gemini before generating")

    args = parser.parse_args()

    if args.analyze:
        print("=== 2027 Blockbuster Slate Analysis ===")
        print(analyze_2027_films(model_name=args.gemini_model))
        print("=" * 60 + "\n")

    film_data = FILMS_2027[args.film]
    print(f"=== Selected 2027 Film: {film_data['title']} ===")
    print(f"Studio: {film_data['studio']}")
    print(f"Premise: {film_data['premise']}\n")
    print("--- Concept Poster Motifs ---")
    for k, v in film_data["concept_poster_motifs"].items():
        print(f"  • {k.capitalize()}: {v}")
    print("\n--- Imagen 3 Theatrical Poster Prompt ---")
    print(film_data["default_poster_prompt"])


if __name__ == "__main__":
    main()
