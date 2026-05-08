from clir import ClirApp

app = ClirApp(name="mycli")

@app.command()
def hello():
    pass

@app.command()
def world():
    pass

print(app.generate_completion("zsh")[:400] + "\n... (truncated)")
