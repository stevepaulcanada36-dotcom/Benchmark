"""Test material. All text written for this benchmark. Sentences are the audio benchmark's S1 set, so the
speech clips already exist and cost nothing to reuse."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "audio"))
from audiobench.prompts import S1 as SENTENCES  # noqa: E402,F401

# Sound effects: (key, prompt, seconds, keywords a correct tag must contain)
EVENTS = [
    ("dog", "a single dog barking twice, close up, no other sounds", 2.0, ["dog", "bark"]),
    ("glass", "a drinking glass falling and shattering on a tile floor", 2.0, ["glass", "shatter", "break", "crash", "smash"]),
    ("knock", "three loud knocks on a wooden door", 2.0, ["knock"]),
    ("applause", "a small crowd applauding and clapping", 3.0, ["applau", "clap"]),
    ("laugh", "one person laughing heartily, no words", 2.5, ["laugh", "chuckl", "giggl"]),
    ("phone", "an old telephone ringing twice", 3.0, ["phone", "ring"]),
]

# Background beds for the noise conditions and the no-speech clips
BEDS = [
    ("cafe", "busy cafe ambience, murmur of distant crowd, cups and dishes clinking, no clear words", 20.0),
    ("street", "city street ambience, passing cars and traffic noise, no voices", 20.0),
]

# L1 acoustic conditions applied to every sentence: (name, bed, SNR in dB or None for clean)
CONDITIONS = [("clean", None, None), ("cafe_10db", "cafe", 10), ("cafe_0db", "cafe", 0), ("street_0db", "street", 0)]

# L5 dialogues: turns alternate between voice A and voice B
DIALOGUES = [
    ["Did you finish the slides for tomorrow?", "Almost. I still need the results table.",
     "I can send you the numbers tonight.", "Perfect, thank you so much."],
    ["Which platform does the train leave from?", "Platform four, but it is running late.",
     "How late are we talking?", "About fifteen minutes, according to the board."],
    ["Can you hear me clearly now?", "Yes, the sound is much better.",
     "Great, I switched to the other microphone.", "Keep that one for the meeting."],
    ["Should we order pizza or noodles?", "Noodles. We had pizza on Monday.",
     "Fair enough. Spicy or mild?", "Medium, and extra vegetables please."],
    ["Where did you park the car?", "Level three, near the elevators.",
     "I looked there and could not find it.", "Then try level two, I might be wrong."],
    ["Is the library open on Sunday?", "Only in the afternoon, from one to five.",
     "That works. I need to return two books.", "Bring your card, they check it now."],
    ["How was the hiking trip?", "Cold, but the view from the top was worth it.",
     "Did you see any wildlife?", "A deer and a lot of very loud birds."],
    ["Who is presenting first today?", "I think Priya is, then the security group.",
     "And when do we go on?", "Right after the break, around eleven."],
]

# L3 no-speech clips: (uid suffix, what it contains, seconds)
NONSPEECH = [
    ("silence_5s", "silence", 5.0), ("silence_15s", "silence", 15.0),
    ("hum_10s", "hum", 10.0), ("white_10s", "white", 10.0),
    ("cafe_10s", "cafe", 10.0), ("street_10s", "street", 10.0),
    ("dog_only", "dog", None), ("glass_only", "glass", None), ("knock_only", "knock", None),
    ("applause_only", "applause", None), ("laugh_only", "laugh", None), ("phone_only", "phone", None),
]
