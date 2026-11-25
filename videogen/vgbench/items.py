"""What gets generated: short storyboards a game developer would need for a sub-1-minute hackathon demo.

Each storyboard is three shots generated separately with the same character and style description, so we can ask
whether a video model keeps the same character, place and state from shot to shot (cross-shot consistency), on top
of whether each clip is stable on its own (within-shot consistency). The character and town are our own invention.
"""

STYLE = ("Cozy hand-painted 2D village seen from a slightly raised three-quarter view, warm autumn colours, soft "
         "daylight, gentle film grain, no real brands, no extra text unless asked.")
HERO = ("Mira, a small round fox character with orange fur, a white-tipped tail, a green knitted scarf and a "
        "straw hat with a red ribbon")

# Each shot: (shot id, what happens). The full prompt is HERO + STYLE + shot text, so every shot shares the same
# description word for word: any drift between shots comes from the model, not from the prompt.
STORYBOARDS = [
    dict(id="SB1", name="Daily visit to the theatre", criteria=["Delightful UX", "Daily Content"],
         carry="The coin counter reads 35 in shot 2 and 27 in shot 3; the red theatre door is the same in both.",
         shots=[("1", "Mira walks along a cobblestone street lined with lanterns towards a small theatre with a red door."),
                ("2", "Mira stands at the red theatre door. A wooden sign in the top-left corner shows a coin icon and the number 35."),
                ("3", "Mira hands a coin to a ticket booth beside the red theatre door. The wooden sign in the top-left corner now shows the number 27.")]),
    dict(id="SB2", name="Boat trip to the island", criteria=["Delightful UX", "Polish"],
         carry="The same small blue boat with a white stripe in all three shots; Mira keeps her scarf and hat.",
         shots=[("1", "Mira walks onto a wooden dock where a small blue rowing boat with a white stripe is tied up."),
                ("2", "Mira sits in the small blue rowing boat with a white stripe, gliding across a calm lake."),
                ("3", "The small blue rowing boat with a white stripe reaches a little island with one cherry tree; Mira steps onto the shore.")]),
    dict(id="SB3", name="Follow camera", criteria=["Polish", "Delightful UX"],
         carry="Camera stays behind and above Mira; the town layout (fountain, bakery with yellow awning) stays the same.",
         shots=[("1", "The camera follows Mira from behind and slightly above as she walks past a stone fountain towards a bakery with a yellow awning."),
                ("2", "Mira turns left at the stone fountain; the camera swings ahead in the direction she is walking."),
                ("3", "Mira stops in front of the bakery with a yellow awning; the camera drifts gently back to centre on her.")]),
    dict(id="SB4", name="Today's challenge", criteria=["Daily Content", "Reddity"],
         carry="The notice board text 'DAY 12' stays readable; the grey cat is the same cat in shots 1 and 3.",
         shots=[("1", "A wooden notice board in the village square shows a paper poster reading 'DAY 12: FIND THE LOST CAT' with a drawing of a grey cat."),
                ("2", "Mira and three other animal villagers gather around the wooden notice board, pointing at the poster reading 'DAY 12'."),
                ("3", "Mira finds a small grey cat hiding under a park bench and smiles; the notice board is visible in the background.")]),
    dict(id="SB5", name="Community vote", criteria=["Reddity", "Daily Content"],
         carry="The lantern count goes from 3 to 5; the same stone bridge and villagers appear in all shots.",
         shots=[("1", "Three glowing paper lanterns hang on a string above a small stone bridge at dusk; Mira stands on the bridge."),
                ("2", "Two animal villagers each hang one more paper lantern on the string above the stone bridge, making five lanterns."),
                ("3", "Five glowing paper lanterns hang above the stone bridge; Mira and the villagers cheer.")]),
    dict(id="SB6", name="Same street, three times of day", criteria=["Polish", "Daily Content"],
         carry="Only the light changes: the street layout, houses and lamp posts must stay identical.",
         shots=[("1", "A quiet village street with three houses (blue, yellow, green) and two lamp posts in the morning sun; Mira waves from the blue house's doorstep."),
                ("2", "The same village street with the blue, yellow and green houses and two lamp posts at sunset, orange light; Mira waves from the blue house's doorstep."),
                ("3", "The same village street with the blue, yellow and green houses and two lamp posts at night, lamps lit; Mira waves from the blue house's doorstep.")]),
]

# A real-world control: if a model fails here too, the problem is not the cartoon style.
CONTROL = dict(id="C1", prompt=("Static close-up of a plain wooden table in a quiet, well-lit room. A pair of hands claps "
                                "exactly three times, slowly, then rests on the table. No music, no speech."))


def clips(cfg):
    """Every clip to make, per model. kind: shot (storyboard), repeat (same seed again), reseed (new seed), control."""
    out = []
    for sb in STORYBOARDS:
        for sid, text in sb["shots"]:
            prompt = f"{HERO}. {text} {STYLE}"
            out.append(dict(cid=f"{sb['id']}-{sid}", sb=sb["id"], shot=sid, kind="shot", prompt=prompt, seed=cfg["seed"]))
        # repeatability on shot 1: same prompt + same seed, and same prompt + a different seed
        p1 = f"{HERO}. {sb['shots'][0][1]} {STYLE}"
        out.append(dict(cid=f"{sb['id']}-1r", sb=sb["id"], shot="1", kind="repeat", prompt=p1, seed=cfg["seed"]))
        out.append(dict(cid=f"{sb['id']}-1s", sb=sb["id"], shot="1", kind="reseed", prompt=p1, seed=cfg["seed"] + 1))
    for r in range(2):
        out.append(dict(cid=f"C1-{r}", sb="C1", shot="1", kind="control", prompt=CONTROL["prompt"], seed=cfg["seed"] + r))
    return out


SB_BY_ID = {s["id"]: s for s in STORYBOARDS}
