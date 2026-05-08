from clir.output import Spinner, Progress
import time

with Spinner("Loading data..."):
    time.sleep(0.3)

with Progress("Indexing files") as p:
    p.set_total(4)
    for _ in range(4):
        time.sleep(0.05)
        p.update(advance=1)
