#!/usr/bin/env python3

"""
Sends updates to a Discord webhook for new changelog entries since the last GitHub Actions publish run.

Automatically figures out the last run and changelog contents with the GitHub API.
"""

import requests
from typing import Iterable

from changelog_helperfunctions import validate_environment, create_session, get_changes, send_text_changelog, send_showcase_changelog, create_changelog_showcase, create_text_changelog, ChangelogEntry


def main():
    if not validate_environment():
        exit(1)

    sess: requests.Session = create_session()
    changes: Iterable[ChangelogEntry] = list(get_changes(sess))

    text_changelog: list[str] = create_text_changelog(sess, changes)
    showcase: dict[str, list] = create_changelog_showcase(sess, changes)
    
    send_text_changelog(text_changelog)
    send_showcase_changelog(showcase)

    return


if __name__ == "__main__":
    main()
