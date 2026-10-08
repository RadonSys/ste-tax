from eval.records import Kind, Task


def task(kind="math", answer=200, terms=(), id="t-1"):
    return Task(id, Kind(kind), "p", answer, tuple(terms), "handwritten", "dev", "MIT")
