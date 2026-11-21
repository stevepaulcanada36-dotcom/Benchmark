"""Prompt suites. All text written for this benchmark (no copyrighted passages).

S1 read-aloud   : plain sentences, scored by WER.
S2 normalization: written forms with the spoken forms we accept; pass if the ASR transcript matches one.
S3 homographs   : the target word is ambiguous in writing; listeners mark right/wrong (ASR cannot hear stress).
S4 expressive   : scripts with audio tags ([whispers], [laughs]...); tags removed for models without tag support.
S5 long-form    : one ~2,000-character passage; WER per ~200-character chunk shows drift and skipped words.
"""

S1 = [
    "The morning train to Kingston was delayed by twenty minutes because of heavy snow.",
    "She packed a notebook, two pencils, and a thermos of hot tea for the long exam.",
    "Our team meets every Tuesday afternoon to review the results from the week before.",
    "The museum will close early on Friday so the staff can prepare the new exhibit.",
    "He forgot his umbrella at the library and walked home in the pouring rain.",
    "Fresh bread from the corner bakery usually sells out before nine in the morning.",
    "The river was calm enough that we could see the reflection of the pine trees.",
    "Please remember to turn off the lights and lock the door when you leave the lab.",
    "A small grey cat followed us all the way from the park to the front steps.",
    "The professor asked each student to explain one assumption behind their model.",
    "Most of the questions on the quiz were about sampling and measurement error.",
    "We drove along the coast for three hours before stopping for lunch in a fishing town.",
    "The new bridge will connect the two halves of the city for the first time in decades.",
    "My grandmother keeps a garden full of tomatoes, beans, and bright yellow marigolds.",
    "The software update fixed the battery problem but introduced a new display bug.",
    "Several volunteers stayed late to clean the hall after the community dinner.",
    "If the weather holds, the festival will open with a concert on the waterfront.",
    "The lecture covered how to report uncertainty when comparing two classifiers.",
    "A strong wind knocked over the recycling bins along the entire street.",
    "Our flight was rebooked twice, so we finally arrived just after midnight.",
    "The children built a tall tower of wooden blocks and then knocked it down laughing.",
    "Researchers collected data from more than four hundred households across the province.",
    "The chef recommended the mushroom soup and a slice of lemon tart for dessert.",
    "Every spring the geese return to the pond behind the old stone church.",
    "The report concluded that the new policy had a small but measurable effect.",
    "He tuned the guitar carefully before playing the first song of the evening.",
    "The hikers reached the summit just as the clouds began to clear.",
    "Remember that the deadline for the final project is the second week of December.",
    "The quiet library on the third floor is the best place to study before exams.",
    "After the storm passed, the whole neighbourhood came outside to clear the branches.",
]

# (written text, [accepted spoken forms])
S2 = [
    ("The startup raised $3.5M last year.", ["the startup raised three point five million dollars last year",
                                              "the startup raised three and a half million dollars last year"]),
    ("Dr. Smith lives on Smith Dr.", ["doctor smith lives on smith drive"]),
    ("The meeting is on 18/11/2026.", ["the meeting is on the eighteenth of november twenty twenty six",
                                       "the meeting is on november eighteenth twenty twenty six",
                                       "the meeting is on eighteen eleven twenty twenty six"]),
    ("Call me at 416-555-0192.", ["call me at four one six five five five zero one nine two",
                                  "call me at four one six five five five oh one nine two"]),
    ("The temperature dropped to -12°C overnight.", ["the temperature dropped to minus twelve degrees celsius overnight",
                                                    "the temperature dropped to negative twelve degrees celsius overnight"]),
    ("Chapter XIV begins on p. 212.", ["chapter fourteen begins on page two hundred twelve",
                                       "chapter fourteen begins on page two hundred and twelve",
                                       "chapter fourteen begins on page two twelve"]),
    ("The flight leaves at 7:45 a.m.", ["the flight leaves at seven forty five a m",
                                        "the flight leaves at seven forty five in the morning"]),
    ("Visit www.example.org/help for details.", ["visit w w w dot example dot org slash help for details",
                                                 "visit example dot org slash help for details"]),
    ("The model scored 87.3% on the test.", ["the model scored eighty seven point three percent on the test"]),
    ("She finished 1st and he finished 22nd.", ["she finished first and he finished twenty second"]),
    ("The package weighs 2.5 kg.", ["the package weighs two point five kilograms",
                                    "the package weighs two and a half kilograms"]),
    ("Take Hwy 401 to exit 365.", ["take highway four oh one to exit three sixty five",
                                   "take highway four zero one to exit three hundred sixty five",
                                   "take highway four oh one to exit three hundred and sixty five"]),
    ("The course code is STA2453H.", ["the course code is s t a two four five three h",
                                      "the course code is s t a twenty four fifty three h"]),
    ("It costs CA$1,250 per term.", ["it costs one thousand two hundred fifty canadian dollars per term",
                                     "it costs twelve hundred fifty canadian dollars per term",
                                     "it costs one thousand two hundred and fifty canadian dollars per term"]),
    ("The ratio was 3:1 in favour.", ["the ratio was three to one in favour"]),
    ("Use the NASA and FBI datasets.", ["use the nasa and f b i datasets"]),
    ("Population: approx. 2.8 million.", ["population approximately two point eight million"]),
    ("The event runs Mon.–Fri.", ["the event runs monday to friday", "the event runs monday through friday"]),
    ("He was born in 1998.", ["he was born in nineteen ninety eight"]),
    ("Set the oven to 180°F.", ["set the oven to one hundred eighty degrees fahrenheit",
                                "set the oven to one hundred and eighty degrees fahrenheit",
                                "set the oven to one eighty degrees fahrenheit"]),
    ("Email allwin@example.com today.", ["email allwin at example dot com today"]),
    ("The fraction 3/4 is larger than 2/3.", ["the fraction three quarters is larger than two thirds",
                                              "the fraction three fourths is larger than two thirds"]),
    ("Room 4B is on the 2nd floor.", ["room four b is on the second floor"]),
    ("Version 2.0.1 fixed the bug.", ["version two point zero point one fixed the bug",
                                      "version two point oh point one fixed the bug"]),
    ("The speed limit is 50 km/h.", ["the speed limit is fifty kilometers per hour",
                                     "the speed limit is fifty kilometres per hour"]),
]

# (text, target word, intended reading) - judged by listeners
S3 = [
    ("I read that book last summer.", "read", "past tense, rhymes with 'red'"),
    ("I read the news every morning.", "read", "present tense, rhymes with 'reed'"),
    ("The pipes were made of lead.", "lead", "the metal, rhymes with 'red'"),
    ("She will lead the team this year.", "lead", "verb, rhymes with 'reed'"),
    ("A tear rolled down his cheek.", "tear", "teardrop, rhymes with 'here'"),
    ("Be careful not to tear the paper.", "tear", "rip, rhymes with 'hair'"),
    ("The wind was strong last night.", "wind", "air, short i"),
    ("Remember to wind the old clock.", "wind", "turn, long i"),
    ("We need to record the results.", "record", "verb, stress on second syllable"),
    ("She set a new world record.", "record", "noun, stress on first syllable"),
    ("They live close to the station.", "close", "near, soft s"),
    ("Please close the window.", "close", "shut, z sound"),
    ("Professor Anantharaj will present the results.", "Anantharaj", "name: a-NUN-tha-raj"),
    ("The paper by Mawson and Donaldson is on the reading list.", "Mawson", "name: MAW-son"),
    ("We met in Mississauga near Lake Ontario.", "Mississauga", "place: miss-iss-AW-ga"),
]

S4 = [
    "[whispers] Don't wake her. She only just fell asleep.",
    "[laughs] I can't believe you actually ate the whole thing!",
    "[excited] We got the grant! All three years are funded!",
    "[sad] I waited at the station for an hour, but nobody came.",
    "[angry] This is the third time the same bug has shipped to production.",
    "[sighs] Fine. I'll redo the analysis from the beginning.",
    "[nervous] Um, is this the right room for the interview?",
    "[calm] Breathe in slowly, hold it for a moment, and let it go.",
    "[sarcastic] Oh great, another meeting that could have been an email.",
    "[shouting] Watch out, the ladder is falling!",
    "[curious] Wait, how did the model get the right answer without the data?",
    "[warmly] Thank you for staying late to help. It really meant a lot.",
]

S5 = (
    "Every autumn, the small town of Alder Point holds a lantern walk along the lakeshore. "
    "Families gather at the old ferry dock just before sunset, carrying paper lanterns they have "
    "folded and painted during the week. Some lanterns are shaped like fish or birds, while others "
    "are simple cylinders covered in drawings of leaves and stars. When the last light fades from "
    "the sky, a volunteer rings the dock bell three times, and the procession begins. "
    "The path follows the water for nearly two kilometres, past the boathouse, the rowing club, and "
    "the stone wall where children like to balance with their arms stretched out. Along the way, "
    "musicians play quiet songs on fiddles and accordions, and the sound carries across the calm "
    "surface of the lake. Older residents remember when the walk was only a handful of people with "
    "candles in jam jars. Today, hundreds of visitors come from nearby cities to take part. "
    "Halfway along the route, the walkers stop at a wooden pavilion where local bakers hand out "
    "warm apple cider and cinnamon buns. Volunteers collect donations for the community library, "
    "which uses the money to buy new books and to keep its doors open on winter evenings. "
    "Last year, the walk raised enough to repair the library roof and to start a weekly reading "
    "club for teenagers. At the far end of the path, the lanterns are placed in a long row on the "
    "breakwater. For a few minutes, nobody speaks. The reflections of the lights tremble on the "
    "dark water, and the only sounds are the waves and the distant call of a loon. Then someone "
    "starts to laugh, conversations begin again, and families slowly make their way home, already "
    "talking about the lanterns they will make next year. For many people in Alder Point, the "
    "walk marks the true start of the season, more than any date on a calendar."
)
