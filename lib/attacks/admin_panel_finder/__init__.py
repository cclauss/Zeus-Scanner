from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
import os
import multiprocessing

try:                 # Python 2
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:  # Python 3
    from urllib.request import urlopen
    from urllib.error import HTTPError

import requests

from var.auto_issue.github import request_issue_creation
from lib.core.settings import (
    logger,
    replace_http,
    set_color,
    create_tree,
    prompt,
    write_to_log_file,
    ROBOTS_PAGE_PATH
)


def check_for_robots(url, ext="/robots.txt", data_sep="-" * 30):
    url = replace_http(url)
    interesting = set()
    full_url = "{}{}{}".format("http://", url, ext)
    conn = requests.get(full_url)
    data = conn.content
    code = conn.status_code
    if code == 404:
        return False
    for line in data.split("\n"):
        if "Allow" in line:
            interesting.add(line.strip())
    if len(interesting) > 0:
        create_tree(full_url, list(interesting))
    else:
        to_display = prompt(
            "nothing interesting found in robots.txt would you like to display the entire page", opts="yN"
        )
        if to_display.lower().startswith("y"):
            print(
                "{}\n{}\n{}".format(
                    data_sep, data, data_sep
                )
            )
    logger.info(set_color(
        "robots.txt page will be saved into a file..."
    ))
    write_to_log_file(data, ROBOTS_PAGE_PATH, "robots-{}.log".format(url))


def check_for_admin_page(url, exts, protocol="http://", **kwargs):
    verbose = kwargs.get("verbose", False)
    show_possibles = kwargs.get("show_possibles", False)
    possible_connections, connections = set(), set()
    stripped_url = replace_http(str(url).strip())
    for ext in exts:
        ext = ext.strip()
        true_url = "{}{}{}".format(protocol, stripped_url, ext)
        if verbose:
            logger.debug(set_color(
                "trying '{}'...".format(true_url), level=10
            ))
        try:
            urlopen(true_url, timeout=5)
            logger.info(set_color(
                "connected successfully to '{}'...".format(true_url)
            ))
            connections.add(true_url)
        except HTTPError as e:
            data = str(e).split(" ")
            if verbose:
                if "Access Denied" in str(e):
                    logger.warning(set_color(
                        "got access denied, possible control panel found without external access on '{}'...".format(
                            true_url
                        ),
                        level=30
                    ))
                    possible_connections.add(true_url)
                else:
                    logger.error(set_color(
                        "failed to connect got error code {}...".format(
                            data[2]
                        ), level=40
                    ))
        except Exception as e:
            if verbose:
                if "<urlopen error timed out>" or "timeout: timed out" in str(e):
                    logger.warning(set_color(
                        "connection timed out after five seconds "
                        "assuming won't connect and skipping...", level=30
                    ))
                else:
                    logger.exception(set_color(
                        "failed to connect with unexpected error '{}'...".format(str(e)), level=50
                    ))
                    request_issue_creation()
    possible_connections, connections = list(possible_connections), list(connections)
    data_msg = "found {} possible connections(s) and {} successful connection(s)..."
    logger.info(set_color(
        data_msg.format(len(possible_connections), len(connections))
    ))
    if len(connections) != 0:
        logger.info(set_color(
            "creating connection tree..."
        ))
        create_tree(url, connections)
    else:
        logger.fatal(set_color(
            "did not receive any successful connections to the admin page of "
            "{}...".format(url), level=50
        ))
    if show_possibles:
        if len(possible_connections) != 0:
            logger.info(set_color(
                "creating possible connection tree..."
            ))
            create_tree(url, possible_connections)
        else:
            logger.fatal(set_color(
                "did not find any possible connections to {}'s "
                "admin page", level=50
            ))


def __load_extensions(filename="{}/etc/link_ext.txt"):
    with open(filename.format(os.getcwd())) as ext:
        return ext.readlines()


def main(url, show=False, verbose=False, **kwargs):
    do_threading = kwargs.get("do_threading", False)
    proc_num = kwargs.get("proc_num", 3)
    logger.info(set_color(
        "parsing robots.txt..."
    ))
    results = check_for_robots(url)
    if not results:
        logger.warning(set_color(
            "seems like this page is blocking access to robots.txt...", level=30
        ))
    logger.info(set_color(
        "loading extensions..."
    ))
    extensions = __load_extensions()
    if verbose:
        logger.debug(set_color(
            "loaded a total of {} extensions...".format(len(extensions)), level=10
        ))
    logger.info(set_color(
        "attempting to bruteforce admin panel..."
    ))
    if do_threading:
        logger.warning(set_color(
            "starting parallel processing with {} processes, this "
            "will depend on your GPU speed...".format(proc_num), level=30
        ))
        tasks = []
        for _ in range(0, proc_num):
            p = multiprocessing.Process(target=check_for_admin_page, args=(url, extensions), kwargs={
                "show_possibles": show,
                "verbose": verbose
            })
            p.start()
            tasks.append(p)
        for proc in tasks:
            proc.join()
    else:
        check_for_admin_page(url, extensions, show_possibles=show, verbose=verbose)