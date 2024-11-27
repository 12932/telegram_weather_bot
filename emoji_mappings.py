from typing import Dict

EMOJI_MAPPINGS: Dict[str, str] = {
    "clear-day": '☀️',
    "clear-night": '🌛',
    "rain": '☔',
    "snow": '❄️',
    "sleet": '❄️',
    "wind": '🌬️',
    "fog": '🌫️',
    "cloudy": '☁️',
    "partly-cloudy-day": '⛅',
    "partly-cloudy-night": '🌛',
    "hail": '☔',
    "thunderstorm": '⛈️',
    "tornado": '🌪️'
}

FORECA_EMOJI_MAPPINGS: Dict[str, str] = {
    "d000": EMOJI_MAPPINGS["clear-day"],
    "d100": EMOJI_MAPPINGS["partly-cloudy-day"],
    "d200": EMOJI_MAPPINGS["partly-cloudy-day"],
    "d210": EMOJI_MAPPINGS["rain"],
    "d220": EMOJI_MAPPINGS["rain"],
    "d300": EMOJI_MAPPINGS["partly-cloudy-day"],
    "d310": EMOJI_MAPPINGS["cloudy"],
    "d320": EMOJI_MAPPINGS["rain"],
    "d340": EMOJI_MAPPINGS["thunderstorm"],
    "d400": EMOJI_MAPPINGS["cloudy"],
    "d420": EMOJI_MAPPINGS["rain"],
    "d430": EMOJI_MAPPINGS["thunderstorm"],
    "n000": EMOJI_MAPPINGS["clear-night"],
    "n100": EMOJI_MAPPINGS["cloudy"],
    "n200": EMOJI_MAPPINGS["cloudy"],
    "n210": EMOJI_MAPPINGS["rain"],
    "n220": EMOJI_MAPPINGS["rain"],
    "n300": EMOJI_MAPPINGS["cloudy"],
    "n320": EMOJI_MAPPINGS["rain"],
    "n400": EMOJI_MAPPINGS["cloudy"],
    "n420": EMOJI_MAPPINGS["rain"],
    "n430": EMOJI_MAPPINGS["thunderstorm"],
}
