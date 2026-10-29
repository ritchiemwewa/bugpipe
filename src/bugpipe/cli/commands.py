from __future__ import annotations

import argparse
import typing as t
from datetime import datetime

from ..api.client import TRACKERS, Bugpipe
from ..api.models import Results
from . import metadata
from .output import FAIL, INFO, OK, console, display, export

if t.TYPE_CHECKING:
    from rich.status import Status

    from ..api.models import CommentsResult, Issue, SearchResult

__all__ = ["parse_args"]


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments and return the populated namespace.

    :return: Parsed arguments with the selected subcommand function in ``.func``.
    """

    parser = argparse.ArgumentParser(
        prog=metadata.pkg_name,
        description=f"{metadata.description}.",
        epilog=f"{metadata.license} © {datetime.now().astimezone().year} {metadata.author}",
    )
    parser.add_argument(
        "-r",
        "--raw",
        action="store_true",
        help="show raw output",
    )
    parser.add_argument(
        "--no-pager",
        action="store_true",
        help="print results straight to the terminal instead of paging them",
    )
    parser.add_argument(
        "-x",
        "--proxy",
        metavar="PROXY_URL",
        help="proxy URL for all requests (e.g. http://localhost:8080)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="request timeout (default %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{metadata.pkg_name} {metadata.version}",
    )
    # Shared by commands that return issue data.
    export_parser = argparse.ArgumentParser(add_help=False)
    export_parser.add_argument(
        "-e",
        "--export",
        action="append",
        choices=["csv", "json"],
        help="export format (repeatable)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    search_parser = subparsers.add_parser(
        "search", parents=[export_parser], help="search for issues"
    )
    search_parser.add_argument("query", help="search query")
    search_parser.add_argument(
        "-t",
        "--tracker",
        action="append",
        choices=[tracker["slug"] for tracker in TRACKERS],
        help="tracker slug",
    )
    search_parser.add_argument(
        "-p",
        "--per-page",
        type=int,
        default=25,
        choices=[25, 50, 100, 250],
        help="results per page (default: 25)",
    )
    search_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="total results to fetch",
    )

    search_parser.set_defaults(func=search)

    # get
    issue_parser = subparsers.add_parser(
        "issue", parents=[export_parser], help="get a single issue"
    )
    issue_parser.add_argument("issue_id", type=int, help="issue ID")
    issue_parser.set_defaults(func=issue)

    # batch
    issues_parser = subparsers.add_parser(
        "issues", parents=[export_parser], help="batch get issues"
    )
    issues_parser.add_argument("issue_ids", type=int, nargs="+", help="issue IDs")
    issues_parser.set_defaults(func=issues)

    # comments
    comments_parser = subparsers.add_parser(
        "comments", parents=[export_parser], help="get comments on an issue"
    )
    comments_parser.add_argument("issue_id", type=int, help="issue ID")
    comments_parser.set_defaults(func=comments)

    # trackers
    subparsers.add_parser("trackers", help="list available trackers")

    # echo (health check)
    echo_parser = subparsers.add_parser(
        "echo",
        help="check whether buganizer is reachable",
        description=(
            "Ping the Buganizer backend (GET /action/yes) and print its "
            "response. 'yes' means the backend is reachable and healthy; "
            "'no' means it is unreachable or returned an error."
        ),
    )
    echo_parser.set_defaults(func=echo)

    args = parser.parse_args()
    args.overrides = __arg_overrides(args, parser, subparsers.choices[args.command])
    return args


def __arg_overrides(args: argparse.Namespace, *parsers: argparse.ArgumentParser) -> dict:
    """
    Collect the options whose value differs from their default.

    :param args: Parsed arguments.
    :param parsers: The parsers that produced them.
    :return: Option name as argparse stores it (``no_pager``) to value.
    """

    return {
        action.dest: getattr(args, action.dest)
        for parser in parsers
        for action in parser._actions
        if action.option_strings
        and action.dest in args
        and getattr(args, action.dest) != action.default
    }


def search(client: Bugpipe, args: argparse.Namespace, status: Status):
    """
    Handle the 'search' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.query``, ``.per_page``, and ``.limit``.
    :param status: Rich status spinner for progress updates.
    """

    query: str = args.query
    per_page: int = args.per_page
    limit: int = args.limit
    tracker_label: str = ", ".join(args.tracker) if args.tracker else "all"

    status.update(
        f"[dim][bold]Searching [italic]{tracker_label}[/] issues for [bold green]{query}[/bold green]…[/dim]"
    )
    result: SearchResult = client.search(query=query, per_page=per_page)
    issues: Results[Issue] = Results(result.issues)

    while limit is not None and result.has_more and len(issues) < limit:
        status.update(
            f"[dim]Collected [cyan]{len(issues)}[/] of [cyan]{limit}[/] issues…[/dim]"
        )
        page: SearchResult | None = client.next_page(result=result)
        if page is None:
            break
        result = page
        issues.extend(result.issues)
    if limit is not None:
        issues = Results(issues[:limit])

    console.log(
        f"{OK} Got {len(issues)} of ~{result.total_count}+ issues for '{query}'"
    )
    console.print("[dim]…[/]")
    status.stop()
    display(output=issues, prettified=args.raw, no_pager=args.no_pager)

    if args.export:
        export(output=issues, formats=args.export)

    if result.has_more:
        console.log(f"{INFO} ~{result.total_count - len(issues)}+ more results available")


def issue(client: Bugpipe, args: argparse.Namespace, status: Status):
    """
    Handle the 'issue' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id: int = args.issue_id
    status.update(f"[dim]Getting issue {issue_id}…[/]")
    issue: Issue = client.issue(issue_id=issue_id)

    status.stop()
    display(output=issue, prettified=args.raw, no_pager=args.no_pager)
    if args.export:
        export(output=issue, formats=args.export)


def issues(client: Bugpipe, args: argparse.Namespace, status: Status):
    """
    Handle the 'issues' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_ids``.
    :param status: Rich status spinner for progress updates.
    """

    issue_ids: list[int] = args.issue_ids
    status.update(f"[dim]Getting issues {issue_ids}…[/]")
    issues: Results[Issue] = client.issues(issue_ids=issue_ids)

    status.stop()
    display(output=issues, prettified=args.raw, no_pager=args.no_pager)
    if args.export:
        export(output=issues, formats=args.export)


def comments(client: Bugpipe, args: argparse.Namespace, status: Status):
    """
    Handle the 'comments' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id: int = args.issue_id

    status.update(status=f"[dim]Getting comments for issue {issue_id}…[/]")
    result: CommentsResult = client.comments(issue_id=issue_id)

    status.stop()
    console.print(f"Issue #{issue_id} — {len(result.comments)} comments\n")
    display(output=result.comments, prettified=args.raw, no_pager=args.no_pager)
    if args.export:
        export(output=result.comments, formats=args.export)


# noinspection PyUnusedLocal
def echo(client: Bugpipe, args: argparse.Namespace, status: Status):
    """
    Handle the 'echo' subcommand: ping the backend and print its response.

    Prints ``echo: yes`` when the backend is reachable and healthy
    , or ``echo: no`` when it is unreachable or returned
    an error.

    :param client: Shared API client instance.
    :param args: Parsed arguments (unused).
    :param status: Rich status spinner for progress updates.
    """

    status.update("[dim]Pinging buganizer…[/dim]")
    response: str = client.echo()
    if response == "yes":
        console.log(f"{OK} echo: {response}")
    else:
        console.log(f"{FAIL} echo: {response}")
