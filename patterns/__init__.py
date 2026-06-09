# Registro de patrones disponibles
from patterns.consolidation import detect as detect_consolidation
from patterns.bounce import detect as detect_bounce
from patterns.impulse import detect as detect_impulse
from patterns.double import detect as detect_double
from patterns.bollinger import detect as detect_bollinger
from patterns.ncandle import detect as detect_ncandle

PATTERN_REGISTRY = {
    "consolidation": detect_consolidation,
    "bounce":        detect_bounce,
    "impulse":       detect_impulse,
    "double":        detect_double,
    "bollinger":     detect_bollinger,
    "ncandle":       detect_ncandle,
}
