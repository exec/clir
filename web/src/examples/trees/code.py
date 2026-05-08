from clir.output import Tree

t = Tree("project")
src = t.branch("src")
src.add("main.py")
src.add("utils.py")
tests = t.branch("tests")
tests.add("test_main.py")
t.add("README.md")
t.show()
