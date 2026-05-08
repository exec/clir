# In docs we render a static representation; the playground will
# bridge actual prompt() calls to a DOM input widget.
from clir.output import Panel, info

Panel(
    "$ name = prompt(\"What is your name?\")\n"
    "  > World\n"
    "$ confirm(\"Continue?\", default=True)\n"
    "  > Y\n"
    "$ select(\"Pick a color:\", [\"red\", \"green\", \"blue\"])\n"
    "  > red",
    title="Interactive prompts (open in playground to try)",
).show()
info("clir's prompt API is non-blocking and integrates with prompt_toolkit.")
