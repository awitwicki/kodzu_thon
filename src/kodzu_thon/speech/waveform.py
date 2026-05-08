import random


def get_waveform(low: int, high: int, count: int) -> list[int]:
    return [random.randrange(low, high) for _ in range(count)]
