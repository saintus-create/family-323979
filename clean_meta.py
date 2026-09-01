#!/usr/bin/env python3
"""
Remove editorial meta commentary from written encyclopedia pages:
- <Info>**Recovered entry.**…</Info>  blocks
- <Warning>**Source data gap.**…</Warning>  blocks
- <Info>**Source data gap.**…</Info>  blocks
- Inline <Note>The source record breaks off…</Note>  spans
- Provenance Accordion notes that mention "source export" / "source record" mid-text
  (but keep the contributor-credit Accordions themselves — just strip the data-gap sentences)
- Note block references to MIGRATION.md and "source export"
"""

import re
import os

def strip_component_block(content: str, tag: str, marker: str) -> str:
    """Remove <tag>…</tag> blocks whose content contains `marker`."""
    pattern = re.compile(
        rf'<{tag}[^>]*>\s*{re.escape(marker)}.*?</{tag}>',
        re.DOTALL
    )
    return pattern.sub('', content)

def strip_inline_note(content: str) -> str:
    """Remove <Note>The source record breaks off…</Note> inline spans."""
    pattern = re.compile(
        r'\s*<Note>The source record[^<]*</Note>',
        re.DOTALL
    )
    return pattern.sub('', content)

def strip_provenance_datagap_sentences(content: str) -> str:
    """
    Inside <Accordion title="Provenance">…</Accordion> blocks,
    remove sentences referencing 'source export' or 'source record' formatting issues.
    (Keep contributor credits.)
    """
    def clean_accord(m):
        inner = m.group(1)
        # Remove sentences about source records being garbled, truncated etc.
        inner = re.sub(
            r'\s*The source record[^.]*\.[^\n]*',
            '',
            inner
        )
        inner = re.sub(
            r'\s*The source record[^.]+\n',
            '\n',
            inner
        )
        return f'<Accordion title="Provenance">{inner}</Accordion>'
    content = re.sub(
        r'<Accordion title="Provenance">(.*?)</Accordion>',
        clean_accord,
        content,
        flags=re.DOTALL
    )
    return content

def clean_file(path: str) -> bool:
    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()

    content = original

    # 1. Remove <Info>**Recovered entry.**…</Info>
    content = strip_component_block(content, 'Info', '**Recovered entry.**')

    # 2. Remove <Warning>**Source data gap.**…</Warning>
    content = strip_component_block(content, 'Warning', '**Source data gap.**')

    # 3. Remove <Info>**Source data gap.**…</Info>
    content = strip_component_block(content, 'Info', '**Source data gap.**')

    # 4. Remove inline <Note>The source record…</Note>
    content = strip_inline_note(content)

    # 5. Clean Provenance accordions
    content = strip_provenance_datagap_sentences(content)

    # 6. Collapse multiple blank lines left behind
    content = re.sub(r'\n{3,}', '\n\n', content)

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
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            if 'Pending migration' in text:
                continue
            if clean_file(path):
                changed.append(path.replace(base + '/', ''))
    print(f"Cleaned {len(changed)} files:")
    for p in changed:
        print(f"  {p}")

if __name__ == '__main__':
    main()
