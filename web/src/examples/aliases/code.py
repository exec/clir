from clir import ClirApp

app = ClirApp(name="mycli")

@app.command()
def hello():
    print("Hello!")

app.aliases.add("hi", "hello")
app.aliases.add("greet", "hello")

print("Resolved 'hi' -->", app.aliases.resolve("hi"))
print("Resolved 'greet' -->", app.aliases.resolve("greet"))
app.run(["hi"])
