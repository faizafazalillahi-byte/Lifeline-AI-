"""
first_aid_guide.py
---------------------
A rule-based "expert system" that returns step-by-step first-aid
guidance the instant an SOS is raised, based on the emergency type and
keywords detected in the user's description.

Honesty note (for the FYP report/viva): this is deliberately NOT
presented as a trained ML model — it's a transparent, explainable
rule-based knowledge system (a classic AI technique in its own right,
predating modern ML). Framing matters: an examiner asking "is this
real AI?" should get an honest "yes, it's a rule-based expert system,
which is a legitimate branch of AI" rather than an overclaim.

IMPORTANT: this is general public-safety guidance only, never a
substitute for professional medical help — every response carries an
explicit disclaimer, and the guidance always tells the user to
call/wait for professional responders.
"""

# Generic steps shown for every alert of a given type, before any more
# specific keyword-matched guidance is appended.
TYPE_LEVEL_STEPS = {
    "medical": [
        "Stay as calm and still as possible while help is on the way.",
        "If you're with someone else, have them stay with you and keep talking to you.",
        "Do not eat or drink anything unless a responder tells you to.",
    ],
    "fire": [
        "Get low and move away from smoke — crawl if the air is thick with smoke.",
        "Do not use elevators. Use stairs if you need to evacuate.",
        "If your clothing catches fire: Stop, Drop, and Roll.",
        "Close doors behind you as you leave to slow the fire's spread.",
    ],
    "accident": [
        "Do not move an injured person unless they are in immediate danger (e.g. fire, traffic).",
        "If safe, turn on hazard lights and place warning triangles/objects to alert other traffic.",
        "Keep the injured person warm and as still as possible.",
    ],
    "crime": [
        "If it's safe to do so, move to a well-lit, populated area.",
        "Stay on the line if you can and describe your surroundings clearly.",
        "Do not confront anyone — prioritize getting to safety over anything else.",
    ],
    "other": [
        "Try to move to a safe, visible location if possible.",
        "Keep your phone charged and location services on so responders can find you.",
    ],
}

# Keyword-triggered ADDITIONAL steps, layered on top of the type-level
# steps above when specific language is detected in the description.
KEYWORD_STEPS = [
    (["bleeding", "blood", "cut", "stabbed"], [
        "Apply firm, direct pressure to the wound with a clean cloth or bandage.",
        "Keep the injured area raised above heart level if possible.",
        "Do not remove the cloth if it soaks through — add more layers on top.",
    ]),
    (["unconscious", "not breathing", "no pulse", "collapsed"], [
        "Check if the person is responsive — tap their shoulder and shout.",
        "If trained, begin CPR: push hard and fast in the center of the chest.",
        "If untrained, follow any instructions given by the emergency call handler.",
    ]),
    (["chest pain", "heart attack"], [
        "Have the person sit down, stay calm, and stop all activity.",
        "Loosen any tight clothing around their neck/chest.",
        "If they carry prescribed heart medication (e.g. aspirin/nitroglycerin), assist them in taking it if appropriate.",
    ]),
    (["burn", "fire", "burnt"], [
        "Cool the burn under cool (not ice-cold) running water for at least 10 minutes.",
        "Do not apply ice, butter, or ointments to the burn.",
        "Cover loosely with a clean, non-stick cloth.",
    ]),
    (["choking", "can't breathe", "cannot breathe"], [
        "If the person can cough or speak, encourage them to keep coughing.",
        "If they cannot breathe/cough/speak, perform back blows and abdominal thrusts (Heimlich maneuver) if trained.",
    ]),
    (["seizure"], [
        "Clear the area of anything the person could hit or injure themselves on.",
        "Do not restrain them or put anything in their mouth.",
        "Turn them gently onto their side once the seizure ends, if possible.",
    ]),
    (["drowning"], [
        "Do not enter deep/fast water yourself unless trained — throw a flotation object instead.",
        "Once out of the water, check for breathing and begin CPR if trained and needed.",
    ]),
    (["fracture", "broken bone", "broken leg", "broken arm"], [
        "Do not try to realign or straighten the injured limb.",
        "Immobilize the area with a splint or rolled cloth/padding if available.",
        "Avoid moving the person unless absolutely necessary.",
    ]),
]

DISCLAIMER = (
    "This is general public-safety guidance only — it is not a substitute for "
    "professional medical care. Continue to wait for emergency responders and "
    "follow any instructions given by a licensed professional or emergency call handler."
)


def get_first_aid_guidance(emergency_type: str, description: str) -> dict:
    """
    Returns {"title": str, "steps": [str, ...], "disclaimer": str}.
    Combines type-level steps with any keyword-matched specific steps,
    de-duplicating while preserving order.
    """
    emergency_type = emergency_type if emergency_type in TYPE_LEVEL_STEPS else "other"
    description_lower = (description or "").lower()

    steps = list(TYPE_LEVEL_STEPS[emergency_type])

    matched_any_keyword = False
    for keywords, extra_steps in KEYWORD_STEPS:
        if any(kw in description_lower for kw in keywords):
            matched_any_keyword = True
            for step in extra_steps:
                if step not in steps:
                    steps.append(step)

    title = "Immediate First-Aid Guidance"
    if matched_any_keyword:
        title = "Immediate First-Aid Guidance (matched to your description)"

    return {
        "title": title,
        "steps": steps,
        "disclaimer": DISCLAIMER,
    }
