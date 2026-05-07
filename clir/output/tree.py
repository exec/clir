"""Tree output component for displaying hierarchical data."""

from __future__ import annotations

from typing import Any, Iterator
from rich.tree import Tree as RichTree
from rich.console import Console

from clir.output.style import get_console


class Tree:
    """A tree for displaying hierarchical data in terminal."""

    def __init__(
        self,
        label: str,
        guide_style: str = "dim",
        expand: bool = False,
    ):
        """Initialize a tree.

        Args:
            label: Root label text
            guide_style: Style for guide lines (default: "dim")
            expand: Whether to expand the tree
        """
        self.label = label
        self.guide_style = guide_style
        self.expand = expand
        self._children: list[tuple[str, "Tree"]] = []
        self._tree: RichTree | None = None

    def add(self, label: str, *labels: str) -> "Tree":
        """Add a branch to the tree.

        Args:
            label: First label
            labels: Additional labels for nested branches

        Returns:
            The added subtree
        """
        if labels:
            # Nested
            subtree = Tree(label)
            subtree.add(*labels)
            self._children.append((label, subtree))
        else:
            # Leaf
            self._children.append((label, None))
        return self

    def branch(self, label: str) -> "Tree":
        """Add a branch and return it for chaining.

        Args:
            label: Branch label

        Returns:
            New Tree instance for the branch
        """
        subtree = Tree(label)
        self._children.append((label, subtree))
        return subtree

    def _build_tree(self, parent: RichTree) -> None:
        """Recursively build the rich tree."""
        for label, subtree in self._children:
            if subtree is None:
                # Leaf node
                parent.add(label)
            else:
                # Branch node - create new subtree
                branch = parent.add(label)
                subtree._build_tree(branch)

    def _to_rich(self) -> RichTree:
        """Convert to Rich Tree."""
        tree = RichTree(
            self.label,
            guide_style=self.guide_style,
            expand=self.expand,
        )
        self._build_tree(tree)
        return tree

    def show(self) -> None:
        """Print the tree to stdout."""
        console = get_console()
        console.print(self._to_rich())

    def __rich__(self) -> RichTree:
        """Rich render protocol."""
        return self._to_rich()


def tree(label: str, *branches: tuple[str, ...]) -> Tree:
    """Create a tree with branches.

    Args:
        label: Root label
        branches: Tuples of branch labels

    Returns:
        Tree instance

    Example:
        t = tree(
            "project",
            ("src", ("main.py", "utils.py")),
            ("tests", ("test_main.py",)),
            ("README.md",),
        )
        t.show()
    """
    t = Tree(label)
    for branch in branches:
        if isinstance(branch, tuple):
            t.add(*branch)
        else:
            t.add(branch)
    return t


__all__ = ["Tree", "tree"]