from pathlib import Path
from typing import Any, Iterable

import re
import os
import yaml
import time
import logging
import colorlog
import requests
import itertools

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    "[%(log_color)s%(levelname)s%(reset)s] %(name)s: %(message)s",
    log_colors={
		"DEBUG": "purple",
		"INFO": "blue",
		"WARNING": "yellow",
		"ERROR": "red",
		"CRITICAL": "red,bg_white",
	}
))

log = logging.getLogger("changelog")
log.setLevel(logging.DEBUG)
log.addHandler(handler)


ChangelogEntry = dict[str, Any]

DEBUG = False
DRY_RUN = False
CHANGELOG_FILE = "Resources/Changelog/Den.yml"

TYPES_TO_EMOJI = {"Fix": "🐛", "Add": "🆕", "Remove": "❌", "Tweak": "⚒️"}

EXPERIMENTAL_LABEL = "Intent: Experimental"
EXPERIMENTAL_EMOJI = "🧪"

# https://discord.com/developers/docs/resources/webhook
DISCORD_SPLIT_LIMIT = 2000
DISCORD_EMBED_LIMIT = 10

DISCORD_WEBHOOK_URL_TEXT = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL_SHOWCASE = os.environ.get("DISCORD_WEBHOOK_URL_SHOWCASE", "")
GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_RUN = os.environ.get("GITHUB_RUN_ID", "1")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

if DEBUG:
    DEBUG_CHANGELOG_FILE_OLD = Path("Resources/Changelog/Old.yml")
    GITHUB_REPOSITORY = "https://github.com/TheDenSS14/TheDenTwo"
    GITHUB_RUN = "1"
    with open(r"Tools\_DEN\changelogs\credentials.txt", "r") as file:
        credentials = file.read().splitlines()
        GITHUB_TOKEN = credentials[1] # replace with your personal access token or the user token from your repository's secrets for debugging DO NOT COMMIT THE FILE WITH THE TOKEN
        DISCORD_WEBHOOK_URL_TEXT = credentials[2] # similar deal with this
        DISCORD_WEBHOOK_URL_SHOWCASE = credentials[3] # similar deal with this


def validate_environment() -> bool:
    """Validates whether the current environment has all the required environment variables. Returns true/false based on success/failure."""

    if not DISCORD_WEBHOOK_URL_TEXT:
        log.error("No text changelog Discord webhook URL found.")
        return False

    if not DISCORD_WEBHOOK_URL_SHOWCASE:
        log.error("No showcase changelog Discord webhook URL found.")
        return False
    
    if not os.environ.get("GITHUB_API_URL"):
        log.warning("No Github API URL found - if the fallback API URL is deprecated, this script will stop working.")
    
    if not GITHUB_REPOSITORY:
        log.error("No Github repository found.")
        return False
    
    if not GITHUB_RUN:
        log.error("No Github run identifier found.")
        return False
    
    if not GITHUB_TOKEN:
        log.error("No Github user token found.")
        return False
    
    return True

def create_session() -> requests.Session:
    """Creates a session using the requests module to be used for interacting with REST APIs."""
    sess = requests.Session()
    sess.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    sess.headers["Accept"] = "Accept: application/vnd.github+json"
    sess.headers["X-GitHub-Api-Version"] = "2026-03-10" # upgrade
    return sess

def get_changes(
    sess: requests.Session
) -> Iterable[ChangelogEntry]:
    if DEBUG:
        log.info("Debug mode active.")
        # to debug this script locally, you can use
        # a separate local file as the old changelog
        # with a couple of entries removed
        with open(DEBUG_CHANGELOG_FILE_OLD, "r", encoding="utf-8-sig") as file:
            last_changelog_stream = file.read()
    else:
        # when running this normally in a GitHub actions workflow,
        # it will get the old changelog from the GitHub API
        last_changelog_stream = get_last_changelog(sess)

    last_changelog = yaml.safe_load(last_changelog_stream)
    with open(CHANGELOG_FILE, "r", encoding="utf-8-sig") as file:
        cur_changelog = yaml.safe_load(file)

    return diff_changelog(last_changelog, cur_changelog) # diff_changelog expects a clean string with no byte order mark otherwise it crashes. ask me how I found out.

def get_most_recent_workflow(
    sess: requests.Session, github_repository: str, github_run: str
) -> Any:
    workflow_run = get_current_run(sess, github_repository, github_run)
    past_runs = get_past_runs(sess, workflow_run)
    for run in past_runs["workflow_runs"]:
        # First past successful run that isn't our current run.
        if run["id"] == workflow_run["id"]:
            continue

        return run


def get_current_run(
    sess: requests.Session, github_repository: str, github_run: str
) -> Any:
    resp = sess.get(
        f"{GITHUB_API_URL}/repos/{github_repository}/actions/runs/{github_run}"
    )
    resp.raise_for_status()
    return resp.json()


def get_past_runs(sess: requests.Session, current_run: Any) -> Any:
    """
    Get all successful workflow runs before our current one.
    """
    params = {"status": "success", "created": f"<={current_run['created_at']}"}
    resp = sess.get(f"{current_run['workflow_url']}/runs", params=params)
    resp.raise_for_status()
    return resp.json()


def get_last_changelog(
    sess: requests.Session
) -> str:
    most_recent = get_most_recent_workflow(sess, GITHUB_REPOSITORY, GITHUB_RUN)
    last_sha = most_recent["head_commit"]["id"]
    log.info(f"Last successful publish job was {most_recent['id']}: {last_sha}")
    last_changelog_stream = get_last_changelog_by_sha(
        sess, last_sha, GITHUB_REPOSITORY
    )

    return last_changelog_stream


def get_last_changelog_by_sha(
    sess: requests.Session, sha: str, github_repository: str
) -> str:
    """
    Use GitHub API to get the previous version of the changelog YAML (Actions builds are fetched with a shallow clone)
    """
    params = {
        "ref": sha,
    }

    resp = sess.get(
        f"{GITHUB_API_URL}/repos/{github_repository}/contents/{CHANGELOG_FILE}",
        params=params,
    )
    resp.raise_for_status()
    return resp.text


def diff_changelog(
    old: dict[str, Any], cur: dict[str, Any]
) -> Iterable[ChangelogEntry]:
    """
    Find all new entries not present in the previous publish.
    """
    old_entry_ids = {e["id"] for e in old["Entries"]}
    return (e for e in cur["Entries"] if e["id"] not in old_entry_ids)

def get_pr_json(
    sess: requests.Session, pr_url: str
) -> Any:
    """Gets the JSON body of the PR using Github's API. The function expects urls in the standard format, not ones already pointing to the API."""
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if match:
        owner, repo, number = match.groups()
        resp = sess.get(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{number}"
        )
        resp.raise_for_status()
        return resp.json()
    else:
        return None

def grab_image_urls_from_pr_body(
    body: str
) -> list[str]:
    """Returns a list of all images contained in HTML tags that appear in the body of the PR. This function expects the body as a string."""
    return re.findall(r'<img[^>]+src="([^"]+)"', body)

def send_discord_webhook(
    json: dict[str, list], url: str
) -> bool:
    """Handles actually sending the webhook, and deals with rate limiting/exceptions. Returns true/false based on success/failure."""
    retry_attempt = 0

    try:
        response = requests.post(url=url, json=json, timeout=10)
        while response.status_code == 429:
            retry_attempt += 1
            if retry_attempt > 20:
                log.error("Too many retries on a single request despite following retry_after header... giving up.")
                return False
            retry_after = response.json().get("retry_after", 5)
            log.info(f"Rate limited, retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            response = requests.post(url=url, json=json, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.exception(f"Failed to send message: {e}")
        return False
    return True

def get_discord_json(content: str):
    return {
        "content": content,
        # Do not allow any mentions.
        "allowed_mentions": {"parse": []},
        # SUPPRESS_EMBEDS
        "flags": 1 << 2,
    }

def create_changelog_showcase(
    sess: requests.Session, changes: Iterable[ChangelogEntry]
) -> dict[str, list]:
    """Creates all the embeds for the showcase changelog, which should only include PRs with images in their body."""
    embeds = {"embeds": [], "allowed_mentions": {"parse": []}}

    for author, changes, _, _, url in (entry.values() for entry in changes):
        pr = get_pr_json(sess, url)

        if not pr:
            log.error(f"Could not find the pull request from: {url}")

        embed = {
            "title": f"{author}",
            "thumbnail": {"url": pr["user"]["avatar_url"]},
            "description": f"### {pr["title"]} [[PR]]({url})",
            "color": int("#81BABA"[1:], base=16), # embeds want an integer color representation for some reason, this allows you to put in a hex value in code and have a preview of the color in your ide
            # change this to whatever color fits your repository
            "fields": []
        }

        images = grab_image_urls_from_pr_body(pr["body"])

        if images:
            embed.update({"image": { "url": images[0] }}) # maybe discord adds nice multi-image embed support later down the line, for now, only the first image.
            log.info(f"Found images in pull request at: {url}")
        else:
            log.info(f"Could not find any images in pull request at: {url}")

        for message, type, labels in ((change["message"], change["type"], change.get("labels", [])) for change in changes):
            emoji = TYPES_TO_EMOJI.get(type, "❓")

            if EXPERIMENTAL_LABEL in labels:
                emoji = f"{emoji}{EXPERIMENTAL_EMOJI}"

            embed["fields"].append({"name":f"", "value":f"{emoji} - {message}"})

        embeds["embeds"].append(embed)

    return embeds

def send_showcase_changelog(
    embeds: dict[str, list]
) -> bool:
    """Sends the showase changelog to Discord, which only includes PRs which have at least one image in their body."""

    message = {"embeds": [], "allowed_mentions": {"parse": []}}
    embed_count: int = 0
    
    for embed in embeds["embeds"]:
        if embed_count >= DISCORD_EMBED_LIMIT:
            log.info("Splitting showcase changelog and sending to discord.")
            if DRY_RUN:
                log.debug("Dry run, nothing sent.")
            else:
                if not send_discord_webhook(message, DISCORD_WEBHOOK_URL_SHOWCASE):
                    exit(1)
            embed_count = 0
            message = {"embeds": [], "allowed_mentions": {"parse": []}}

        if "image" in embed: # showcase should only contain embeds with images
            message["embeds"].append(embed)
            embed_count += 1


    if len(message["embeds"]) > 0:
        log.info("Sending final showcase changelog to discord.")
        if DRY_RUN:
            log.debug("Dry run, nothing sent.")
        else:
            if not send_discord_webhook(message, DISCORD_WEBHOOK_URL_SHOWCASE):
                exit(1)

    
    return True

def create_text_changelog(
    sess: requests.Session, changes: Iterable[ChangelogEntry]
) -> list[str]:
    """Creates a text-based changelog without any media or embeds."""

    message_lines = []

    for contributor_name, group in itertools.groupby(changes, lambda x: x["author"]):
        message_lines.append(f"\n**{contributor_name}** updated:\n")

        for entry in group:
            url = entry.get("url")
            if url and not url.strip():
                url = None

            for change in entry["changes"]:
                emoji = TYPES_TO_EMOJI.get(change["type"], "❓")
                message = change["message"]

                if EXPERIMENTAL_LABEL in entry.get("labels", []):
                    emoji = f"{emoji}{EXPERIMENTAL_EMOJI}"

                # if a single line is longer than the limit, it needs to be truncated
                if len(message) > DISCORD_SPLIT_LIMIT:
                    message = message[: DISCORD_SPLIT_LIMIT - 100].rstrip() + " [...]"

                if url is not None:
                    pr_number = url.split("/")[-1]
                    line = f"{emoji} - {message} ([#{pr_number}]({url}))\n"
                else:
                    line = f"{emoji} - {message}\n"

                message_lines.append(line)

    return message_lines


def send_text_changelog(
        message_lines: list[str]
) -> bool:
    """Handles the Discord character limit and actually sending the text-based changelog."""

    chunk_lines = []
    chunk_length = 0

    for line in message_lines:
        line_length = len(line)
        new_chunk_length = chunk_length + line_length

        if new_chunk_length > DISCORD_SPLIT_LIMIT:
            log.info("Splitting text changelog and sending to discord.")
            if DRY_RUN:
                log.debug("Dry run, nothing sent.")
            else:
                send_discord_webhook(
                    get_discord_json(
                        "".join(chunk_lines)), DISCORD_WEBHOOK_URL_TEXT)

            new_chunk_length = line_length
            chunk_lines.clear()

        chunk_lines.append(line)
        chunk_length = new_chunk_length

    if chunk_lines:
        log.info("Sending final text changelog to discord.")
        if DRY_RUN:
            log.debug("Dry run, nothing sent.")
        else:
            send_discord_webhook(
                get_discord_json(
                    "".join(chunk_lines)), DISCORD_WEBHOOK_URL_TEXT)

    return True