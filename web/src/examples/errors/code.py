from clir import ClirApp, ClirError, UsageError

app = ClirApp(name="demo")

@app.command()
def bad():
    raise UsageError("Missing required --name flag.")

try:
    app.run(["bad"])
except SystemExit as e:
    print(f"\nExit code was: {e.code}")
