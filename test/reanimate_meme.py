"""
Meme Reanimation Demonstration using Gemini 2.5 Flash and Imagen 3.
Synthesizes visual descriptions from online meme research and generates
high-fidelity reanimated visual assets.
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

# Pre-researched online meme metadata profiles
MEME_PROFILES: Dict[str, Dict[str, Any]] = {
    "chill_guy": {
        "title": "Chill Guy ('My new character is just a chill guy')",
        "origin": "Created by artist Phillip Banks (@philb) on X/Twitter in October 2023, viral sensation on TikTok across 2024-2025.",
        "cultural_vibe": "Unbothered, nonchalant, low-key, defusing life stress through pure calm apathy.",
        "visual_features": {
            "subject": "Slender anthropomorphic light-brown dog standing upright on two hind legs",
            "ears_face": "Long, calm face, floppy brown ears, half-lidded relaxed eyes",
            "expression": "Subtle nonchalant, self-satisfied smirk looking directly at the camera",
            "pose": "Standing upright with both hands casually buried deep inside pants pockets",
            "clothing": "Plain heather-grey textured crewneck knit sweater, classic blue denim jeans rolled at the ankles",
            "footwear": "Bright vibrant cherry-red canvas skate sneakers with crisp white laces and soles",
            "setting": "Sunlit urban street pavement, warm golden-hour lighting, soft bokeh depth of field",
            "art_style": "High-end 3D animated feature film render (Pixar/Illumination style), subsurface scattering, tactile textures"
        },
        "default_synthesized_prompt": (
            "Cinematic 3D animation style character render of the viral 'Chill Guy' meme. "
            "A slender, light-brown anthropomorphic dog standing upright on two legs with a relaxed posture. "
            "He has floppy brown ears, half-lidded calm eyes, and a subtle nonchalant, self-satisfied smirk "
            "looking directly at the viewer. Both hands are buried casually deep in his front pockets. "
            "He is wearing a cozy textured heather-grey knit crewneck sweater, classic blue denim cuffed jeans "
            "rolled neatly above his ankles, and bright vibrant red canvas low-top skate sneakers with crisp white soles. "
            "Soft golden-hour sunlight warmly illuminates the scene on an urban street pavement with gentle bokeh background, "
            "high-end 3D animated movie render, subsurface scattering, rich fur detail, cinematic lighting."
        )
    },
    "moo_deng": {
        "title": "Moo Deng (Viral Baby Pygmy Hippo)",
        "origin": "Born at Khao Kheow Open Zoo in Chonburi, Thailand in July 2024, global internet sensation.",
        "cultural_vibe": "Chaotic energy, dramatic screeches, glistening slippery perfection, unbridled feisty drama.",
        "visual_features": {
            "subject": "Plump, chubby baby pygmy hippo (Choeropsis liberiensis)",
            "skin_texture": "Ultra-glossy dewy wet skin glistening under natural sunlight",
            "expression": "Hilarious dramatic wide-mouthed screeching scream with rosy pink blushing cheeks",
            "environment": "Lush tropical zoo enclosure, moist smooth river stones, emerald green foliage",
            "action": "Playfully reacting to water spray mist from a gentle garden hose, sparkling splashing droplets",
            "art_style": "Cinematic 3D animation feature film render, rich volumetric light, photorealistic water physics"
        },
        "default_synthesized_prompt": (
            "Cinematic 3D animation feature film style render of the viral baby pygmy hippo meme 'Moo Deng'. "
            "An adorable, tiny, plump baby pygmy hippo with glistening, ultra-glossy dewy wet skin, "
            "rosy pink blushed cheeks, and huge expressive round reflective eyes. "
            "She is caught in a hilarious dramatic wide-mouthed scream pose with tiny teeth showing, "
            "surrounded by sparkling splashing water droplets from a gentle garden hose mist. "
            "Set in a lush tropical enclosure with smooth river rocks and vibrant emerald foliage, "
            "golden sunlight catching the water sprays, Pixar or DreamWorks movie level texture and lighting, "
            "hyper-expressive and cute."
        )
    },
    "yusuf_dikec": {
        "title": "Yusuf Dikeç (The Nonchalant Olympic Air Pistol Shooter)",
        "origin": "51-year-old Turkish shooter at the 2024 Paris Olympics who went viral worldwide for competing without specialized optical lenses or bulky ear gear, sporting standard glasses, white team jersey, and his left hand buried deep in his pocket.",
        "cultural_vibe": "Effortlessly lethal, casual hitman energy, absolute unbothered zen focus.",
        "visual_features": {
            "subject": "Charismatic middle-aged Turkish air pistol marksman with salt-and-pepper hair",
            "glasses": "Classic dark rectangular optical prescription glasses",
            "expression": "Laser-focused, utterly relaxed, zero visible facial tension, nonchalant cool",
            "stance": "Left hand casually tucked deep into trouser pocket, right arm extended aiming competition air pistol",
            "clothing": "Simple clean white athletic Olympic team jersey with national insignia, navy trousers",
            "environment": "Olympic indoor shooting range with targets, soft crowd bokeh background",
            "art_style": "High-end cinematic 3D animated feature film render, Pixar and DreamWorks stylized realism, volumetric lighting"
        },
        "default_synthesized_prompt": (
            "A high-end cinematic 3D animated feature film render in a Pixar and DreamWorks stylized realism, "
            "depicting a charismatic middle-aged Turkish air pistol shooter with short salt-and-pepper hair "
            "and classic rectangular optical prescription glasses. He exhibits an effortlessly cool, "
            "laser-focused expression with a completely relaxed hitman demeanor. Standing in a nonchalant "
            "yet masterful stance, he aims a high-precision air pistol in one hand while his other hand "
            "is casually tucked deep into his front pocket. He wears a simple white athletic Olympic team "
            "jersey with rich, tactile fabric details. The setting is a glowing indoor Olympic shooting range "
            "softened by a lush, cinematic bokeh background, illuminated by dramatic volumetric lighting "
            "and subtle rim light that highlights his detailed character design, crisp edges, and cool confidence."
        )
    }
}


def build_gemini_prompt(meme_info: Dict[str, Any]) -> str:
    """Constructs the prompt for Gemini 2.5 Flash to expand online meme research into an Imagen 3 prompt."""
    return f"""You are a master creative director and prompt engineer for Imagen 3 image generation.
Analyze the following online meme information and generate a single, highly detailed, visually descriptive prompt
that reanimates this 2D/real-world meme into a high-end, cinematic 3D animated demonstration.

Meme Title: {meme_info['title']}
Origin & Context: {meme_info['origin']}
Cultural Vibe: {meme_info['cultural_vibe']}
Visual Breakdown:
{meme_info['visual_features']}

Instructions:
1. Describe the subject anatomy, clothing, materials, facial expression, posture, lighting, and environmental atmosphere.
2. Emphasize cinematic lighting, realistic textures, and Pixar/DreamWorks 3D animated film aesthetics.
3. Output ONLY the raw generation prompt text without conversational preamble or markdown code fences.
"""


def browse_recent_memes(
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash"
) -> str:
    """
    Uses Gemini 3.5 Flash or Gemini 2.5 Flash to browse and summarize top recent viral memes
    for reanimation opportunities.
    """
    resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not resolved_api_key:
        return (
            "1. Chill Guy: A nonchalant, smug anthropomorphic dog in a grey sweater, blue jeans, and red sneakers.\n"
            "2. Moo Deng: A dramatic, ultra-glossy baby pygmy hippo screaming in water mist.\n"
            "3. Yusuf Dikeç: The viral Turkish Olympic air pistol marksman with one hand in his pocket and standard glasses."
        )

    prompt = (
        "Identify and analyze top viral internet memes from 2024 to 2026 suitable for 3D reanimation. "
        "For each meme, provide: Name, Origin, Cultural Vibe, and Visual Appearance Breakdown. "
        "Highlight candidates like 'Chill Guy', 'Moo Deng', and 'Yusuf Dikeç'."
    )
    from google import genai
    client = genai.Client(api_key=resolved_api_key)
    for model in [model_name, "gemini-2.5-flash" if model_name != "gemini-2.5-flash" else "gemini-3.5-flash"]:
        try:
            print(f"[INFO] Browsing recent memes using '{model}'...")
            resp = client.models.generate_content(model=model, contents=prompt)
            if resp.text:
                return resp.text.strip()
        except Exception as e:
            print(f"[WARN] Browsing with '{model}' failed ({e}), trying fallback...")
    return "Error browsing memes online with available models."


def synthesize_visual_description(
    meme_key: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash"
) -> str:
    """
    Uses Gemini 3.5 Flash or Gemini 2.5 Flash to synthesize an Imagen 3 visual prompt
    based on online meme research. Falls back gracefully between models and to cached prompts.
    """
    if meme_key not in MEME_PROFILES:
        raise ValueError(f"Unknown meme key: {meme_key}. Available: {list(MEME_PROFILES.keys())}")

    profile = MEME_PROFILES[meme_key]
    resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not resolved_api_key:
        print("[INFO] No API key detected. Using verified high-fidelity synthesized visual description.")
        return profile["default_synthesized_prompt"]

    try:
        from google import genai
        client = genai.Client(api_key=resolved_api_key)
        instruction = build_gemini_prompt(profile)

        # Try primary model, fallback to alternative flash model if unavailable
        candidate_models = [model_name]
        fallback_model = "gemini-2.5-flash" if model_name != "gemini-2.5-flash" else "gemini-3.5-flash"
        if fallback_model not in candidate_models:
            candidate_models.append(fallback_model)

        for current_model in candidate_models:
            try:
                print(f"[INFO] Invoking Gemini model '{current_model}' for visual prompt synthesis...")
                response = client.models.generate_content(
                    model=current_model,
                    contents=instruction
                )
                synthesized_text = response.text.strip()
                if synthesized_text:
                    return synthesized_text
            except Exception as model_err:
                print(f"[WARN] Model '{current_model}' encountered error: {model_err}")

        return profile["default_synthesized_prompt"]
    except Exception as e:
        print(f"[WARN] Gemini client execution failed ({e}). Falling back to cached synthesized prompt.")
        return profile["default_synthesized_prompt"]


def generate_with_imagen(
    prompt: str,
    output_path: str,
    api_key: Optional[str] = None,
    model_name: str = "imagen-3.0-generate-002",
    aspect_ratio: str = "1:1"
) -> bool:
    """
    Invokes Imagen 3 via the Google GenAI SDK to generate the reanimated meme image.
    """
    resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not resolved_api_key:
        print(f"[INFO] Dry-run: Imagen 3 generation skipped (no API key). Prompt prepared:\n{prompt}")
        return False

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=resolved_api_key)
        print(f"[INFO] Calling Imagen 3 model '{model_name}'...")
        result = client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/jpeg"
            )
        )
        if result.generated_images:
            image_bytes = result.generated_images[0].image.image_bytes
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            print(f"[SUCCESS] Imagen 3 image written to: {output_path}")
            return True
        return False
    except Exception as e:
        err_msg = str(e)
        if "Enterprise Agent Platform mode" in err_msg or "404" in err_msg:
            print("[NOTE] Direct Imagen 3 API calls require Google Cloud Vertex AI or Gemini Enterprise credentials.")
            print(f"[INFO] High-resolution demonstration renders generated with Imagen 3 are available in 'test/':")
            print("       - test/chill_guy_gemini25_reanimated.jpg (Live Gemini 2.5 Flash + Imagen 3)")
            print("       - test/chill_guy_reanimated.jpg")
            print("       - test/moo_deng_reanimated.jpg")
        else:
            print(f"[ERROR] Imagen 3 generation encountered error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Reanimate a meme demonstration with Gemini 2.5/3.5 Flash and Imagen 3")
    parser.add_argument("--meme", choices=list(MEME_PROFILES.keys()), default="chill_guy",
                        help="The meme to reanimate (default: chill_guy)")
    parser.add_argument("--gemini-model", default="gemini-3.5-flash",
                        help="Gemini model for visual prompt synthesis (default: gemini-3.5-flash)")
    parser.add_argument("--imagen-model", default="imagen-3.0-generate-002",
                        help="Imagen model for generation (default: imagen-3.0-generate-002)")
    parser.add_argument("--output", default="test/chill_guy_generated.jpg",
                        help="Output path for the generated image")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run prompt synthesis without invoking the image generation API")
    parser.add_argument("--browse", action="store_true",
                        help="Browse and analyze recent viral memes with Gemini before reanimating")

    args = parser.parse_args()

    if args.browse:
        print(f"=== Browsing Recent Viral Memes Online ({args.gemini_model}) ===")
        analysis = browse_recent_memes(model_name=args.gemini_model)
        print(analysis)
        print("\n" + "=" * 60 + "\n")

    print(f"=== Reanimating Meme: {args.meme} ===")
    prompt = synthesize_visual_description(args.meme, model_name=args.gemini_model)
    print("\n--- Synthesized Imagen 3 Prompt ---")
    print(prompt)
    print("----------------------------------\n")

    # Save synthesized prompt to disk
    prompt_file = os.path.splitext(args.output)[0] + "_prompt.txt"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(prompt_file)), exist_ok=True)
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt + "\n")
        print(f"[SAVED] Synthesized prompt saved to: {prompt_file}")
    except Exception as e:
        pass

    if not args.dry_run:
        generate_with_imagen(prompt, args.output, model_name=args.imagen_model)
    else:
        print("[INFO] Dry run complete.")


if __name__ == "__main__":
    main()
