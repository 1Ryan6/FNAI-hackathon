# Meme Reanimation Demonstration: Gemini 2.5 Flash & Imagen 3

This directory contains the demonstration and test suite for reanimating viral internet memes using **Gemini 2.5 Flash** (for contextual analysis and visual prompt synthesis) and **Imagen 3** (for high-fidelity cinematic image generation).

---

## 🎨 Reanimated Demonstrations

### 1. "Yusuf Dikeç" (The Casual Olympic Shooter)
* **Online Meme Context**: 51-year-old Turkish marksman who captivated the internet at the 2024 Paris Olympics by competing casually without specialized lenses or ear gear, one hand buried deep in his pocket.
* **Gemini 3.5 Flash Synthesized Prompt**:
  > *"A high-end cinematic 3D animated feature film render in a Pixar and DreamWorks stylized realism, depicting a charismatic middle-aged Turkish air pistol shooter with short salt-and-pepper hair and classic rectangular optical prescription glasses. He exhibits an effortlessly cool, laser-focused expression with a completely relaxed hitman demeanor. Standing in a nonchalant yet masterful stance, he aims a high-precision air pistol in one hand while his other hand is casually tucked deep into his front pocket. He wears a simple white athletic Olympic team jersey with rich, tactile fabric details. The setting is a glowing indoor Olympic shooting range softened by a lush, cinematic bokeh background, illuminated by dramatic volumetric lighting and subtle rim light that highlights his detailed character design, crisp edges, and cool confidence."*
* **Generated Asset**: `test/yusuf_dikec_reanimated.jpg`

### 2. "Chill Guy" ("My new character is just a chill guy")
* **Online Meme Context**: Created by artist Phillip Banks (@philb) and popularized globally on TikTok. Represents total nonchalance, calm apathy, and an unbothered attitude in the face of chaos.
* **Gemini 2.5 Flash Synthesized Prompt**:
  > *"Cinematic 3D animation style character render of the viral 'Chill Guy' meme. A slender, light-brown anthropomorphic dog standing upright on two legs with a relaxed posture. He has floppy brown ears, half-lidded calm eyes, and a subtle nonchalant, self-satisfied smirk looking directly at the viewer. Both hands are buried casually deep in his front pockets. He is wearing a cozy textured heather-grey knit crewneck sweater, classic blue denim cuffed jeans rolled neatly above his ankles, and bright vibrant red canvas low-top skate sneakers with crisp white soles. Soft golden-hour sunlight warmly illuminates the scene on an urban street pavement with gentle bokeh background, high-end 3D animated movie render, subsurface scattering, rich fur detail, cinematic lighting."*
* **Generated Assets**:
  * `test/chill_guy_gemini25_reanimated.jpg` (Live Gemini 2.5 Flash prompt synthesis + Imagen 3)
  * `test/chill_guy_reanimated.jpg` (Baseline 3D animation render)

### 2. "Moo Deng" (Viral Baby Pygmy Hippo)
* **Online Meme Context**: Born at Khao Kheow Open Zoo in Thailand. Captured the internet with dramatic wide-mouthed screaming, slippery dewy skin, and unhinged playful drama when misted with garden hoses.
* **Gemini 2.5 Flash Synthesized Prompt**:
  > *"Cinematic 3D animation feature film style render of the viral baby pygmy hippo meme 'Moo Deng'. An adorable, tiny, plump baby pygmy hippo with glistening, ultra-glossy dewy wet skin, rosy pink blushed cheeks, and huge expressive round reflective eyes. She is caught in a hilarious dramatic wide-mouthed scream pose with tiny teeth showing, surrounded by sparkling splashing water droplets from a gentle garden hose mist. Set in a lush tropical enclosure with smooth river rocks and vibrant emerald foliage, golden sunlight catching the water sprays, Pixar or DreamWorks movie level texture and lighting, hyper-expressive and cute."*
* **Generated Asset**: `test/moo_deng_reanimated.jpg`

---

## 📂 Directory Contents

* **`reanimate_meme.py`**: Demonstration script implementing the full prompt synthesis and Imagen 3 generation pipeline. Supports both dry-run and live API execution via the `google-genai` SDK.
* **`test_meme_reanimation.py`**: Complete unit test suite verifying schema validation, prompt construction, Gemini 2.5 Flash synthesis mocking, Imagen 3 generation, and image asset validation.
* **`chill_guy_reanimated.jpg`**: Imagen 3 generated demonstration asset for the Chill Guy meme.
* **`moo_deng_reanimated.jpg`**: Imagen 3 generated demonstration asset for the Moo Deng meme.

---

## 🚀 Running the Demonstration

### 1. Run the Test Suite
```bash
python3 test/test_meme_reanimation.py
```

### 2. Run Meme Reanimation Dry-Run
```bash
python3 test/reanimate_meme.py --meme chill_guy --dry-run
python3 test/reanimate_meme.py --meme moo_deng --dry-run
```

### 3. Live Execution with API Key
To invoke live Gemini 2.5 Flash and Imagen 3 generation:
```bash
export GEMINI_API_KEY="your-api-key-here"
python3 test/reanimate_meme.py --meme chill_guy --output test/chill_guy_custom.jpg
```

---

## 🎬 2027 Blockbuster Film Concept Posters

* **`generate_2027_film_poster.py`**: Analyzes 5 potential 2027 films (*The Batman: Arkham Descends*, *Superman: Man of Tomorrow*, *A Minecraft Movie 2*, *Sky Rat*, *Teenage Mutant Ninja Turtles: Mutant Mayhem 2*) and synthesizes concept poster prompts.
* **`test_2027_film_posters.py`**: Unit test suite for 2027 film profiles and poster rendering validation.
* **`the_batman_2027_poster.jpg`**: Unofficial theatrical 2:3 release poster for *The Batman*.
* **`superman_2027_poster.jpg`**: Unofficial theatrical 2:3 release poster for *Superman*.
* **`sky_rat_2027_poster.jpg`**: Unofficial theatrical 2:3 release poster for *Sky Rat*.

### Running the 2027 Poster Generator & Tests
```bash
# Run 2027 film poster test suite:
python3 test/test_2027_film_posters.py

# Inspect film concept motifs & prompts:
python3 test/generate_2027_film_poster.py --film sky_rat
python3 test/generate_2027_film_poster.py --film teenage_mutant_ninja_turtles_part_2
python3 test/generate_2027_film_poster.py --film batman_arkham_descends
```

