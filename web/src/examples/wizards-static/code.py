from clir.output import Panel

Panel(
    "Step 1/3: project name → my-app\n"
    "Step 2/3: language    → Python\n"
    "Step 3/3: use a database? → Yes\n\n"
    "Result: {'name': 'my-app', 'language': 'Python', 'database': 'Yes'}",
    title="Wizard (multi-step prompt flow)",
).show()
