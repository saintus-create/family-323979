#!/usr/bin/env python3
"""
Upgrade encyclopedia MDX pages to use Fern component library:
1. Replace "See also [X](/path)" lines with CardGroup pill navigation
2. Add entry-type Badge after the Lead component
"""

import re
import os

# Entry type classification for badges
ENTRY_TYPES = {
    # Figures of speech / rhetorical figures
    "accumulatio.mdx": ("Figure of Speech", "note"),
    "actio.mdx": ("Canon of Rhetoric", "info"),
    "anacoluthon.mdx": ("Figure of Speech", "note"),
    "anadiplosis.mdx": ("Figure of Speech", "note"),
    "anaphora.mdx": ("Figure of Speech", "note"),
    "anapodoton.mdx": ("Figure of Speech", "note"),
    "anastrophe.mdx": ("Figure of Speech", "note"),
    "antanaclasis.mdx": ("Figure of Speech", "note"),
    "anthimeria.mdx": ("Figure of Speech", "note"),
    "antithesis.mdx": ("Figure of Speech", "note"),
    "asterismos.mdx": ("Figure of Speech", "note"),
    "asyndeton.mdx": ("Figure of Speech", "note"),
    # Works / treatises
    "antidosis.mdx": ("Classical Work", "tip"),
    "ars-praedicandi.mdx": ("Classical Work", "tip"),
    # Scholars / rhetors / philosophers
    "alcuin-of-york.mdx": ("Rhetorician", "success"),
    "aspasia-of-miletus.mdx": ("Rhetorician", "success"),
    "aristotle.mdx": ("Philosopher", "success"),
    "austin-jl-19111960.mdx": ("Philosopher", "success"),
    "aytoun-edward-edmondstoune.mdx": ("Rhetorician", "success"),
    "ayer-alfred-jules.mdx": ("Philosopher", "success"),
    "barthes-roland-19151980.mdx": ("Theorist", "success"),
    "bentham-jeremy-17481832.mdx": ("Philosopher", "success"),
    "berthoff-ann-e-b-1924.mdx": ("Rhetorician", "success"),
    "britton-james-19081994.mdx": ("Linguist", "success"),
    "burke-kenneth.mdx": ("Rhetorician", "success"),
    "bede-672-or-673735-ce.mdx": ("Rhetorician", "success"),
    # Concepts / fields
    "advertising-rhetoric-of.mdx": ("Field", "launch"),
    "african-american-rhetoric.mdx": ("Field", "launch"),
    "argument.mdx": ("Concept", "info"),
    "arrangement.mdx": ("Canon of Rhetoric", "info"),
    "atticism.mdx": ("Style", "info"),
    "author.mdx": ("Concept", "info"),
    "axiology.mdx": ("Concept", "info"),
    "basic-english.mdx": ("Concept", "info"),
    "basic-writing.mdx": ("Field", "launch"),
    "basic-concepts-operant.mdx": ("Concept", "info"),
}

# Icon for "See also" cards — a single consistent icon
SEE_ALSO_ICON = "fa-regular fa-book-open"


def build_card_group(links: list) -> str:
    """Build a CardGroup MDX block from (title, path) pairs."""
    cols = min(len(links), 3)
    lines = [f'<CardGroup cols={{{cols}}}>']
    for title, path in links:
        lines.append(f'  <Card')
        lines.append(f'    title="{title}"')
        lines.append(f'    icon="{SEE_ALSO_ICON}"')
        lines.append(f'    href="{path}"')
        lines.append(f'  />')
    lines.append('</CardGroup>')
    return '\n'.join(lines)


def upgrade_see_also(content: str) -> str:
    """
    Replace 'See also [X](/path), [Y](/path) and [Z](/path).' patterns
    with CardGroup components. The "See also" line may be a single line
    or span two lines (link-list continuations).
    Strategy: scan line by line; if a line starts with "See also",
    collect it plus any immediate continuation lines that are pure link lists,
    then replace the whole block.
    """
    lines = content.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect start of a "See also" block
        if re.match(r'^See also\s+', line, re.IGNORECASE):
            # Collect this line and any following lines that are just links / "and" links
            block_lines = [line]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                # A continuation line is one that has markdown links and
                # starts with "and" or starts directly with a link "[" or is empty
                if nxt and re.match(r'^(?:and\s+)?\[', nxt):
                    block_lines.append(lines[j])
                    j += 1
                else:
                    break
            block_text = ' '.join(bl.strip() for bl in block_lines)
            # Extract all links from the block
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', block_text)
            if links:
                result.append(build_card_group(links))
                i = j
                continue
        result.append(line)
        i += 1
    return '\n'.join(result)


def add_badge(content: str, filename: str) -> str:
    """Add an entry-type Badge right after the closing </Lead> tag."""
    key = os.path.basename(filename)
    if key not in ENTRY_TYPES:
        return content
    label, intent = ENTRY_TYPES[key]
    badge_line = f'\n<Badge intent="{intent}">{label}</Badge>\n'
    # Only add if no badge yet
    if '<Badge' in content:
        return content
    content = content.replace('</Lead>', '</Lead>' + badge_line, 1)
    return content


def upgrade_file(path: str) -> bool:
    """Upgrade a single MDX file. Returns True if modified."""
    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()

    content = original
    content = upgrade_see_also(content)
    content = add_badge(content, path)

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    base = '/home/user/family-323979/fern/docs/pages/encyclopedia'
    changed = []
    for root, dirs, files in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith('.mdx'):
                continue
            path = os.path.join(root, fn)
            # Skip migration stubs — only upgrade written pages
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            if 'Pending migration' in text:
                continue
            if upgrade_file(path):
                changed.append(path.replace(base + '/', ''))
    print(f"Modified {len(changed)} files:")
    for p in changed:
        print(f"  {p}")


if __name__ == '__main__':
    main()
