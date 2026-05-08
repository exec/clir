from clir import ClirApp, argument, option

app = ClirApp(name="mycli", description="A small CLI demonstrating commands and groups.")

@app.command()
@argument("name")
@option("--count", "-c", default=1)
def greet(name: str, count: int):
    """Greet someone warmly."""
    for _ in range(count):
        print(f"Hello, {name}!")

@app.group()
def db():
    """Database operations."""
    pass

@db.command()
def migrate():
    """Run pending migrations."""
    print("Migrations applied.")

app.run(["--help"])
