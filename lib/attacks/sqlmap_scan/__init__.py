from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
import json
import time
import re
import subprocess

try:
    import urllib.request, urllib.error, urllib.parse  # python 2
except ImportError:
    import urllib as urllib2  # python 3

import requests

import lib.core.settings
import lib.core.errors

from var.auto_issue.github import request_issue_creation


class SqlmapHook(object):

    """
    Sqlmap API hook, will process API requests, and output API data
    """

    def __init__(self, to_scan, port=None, api_con="http://127.0.0.1:{}", default_port=8775):
        self.to_scan = to_scan
        self.port = port or default_port
        self.headers = {"Content-Type": "application/json"}
        self.connection = api_con.format(self.port)
        self.commands = {
            "init": "/task/new",
            "id": "/admin/0/list",
            "start": "/scan/{}/start",
            "status": "/scan/{}/status",
            "log": "/scan/{}/log"
        }

    def init_new_scan(self):
        """
        create a new API scan
        """
        new_scan_url = "{}{}".format(self.connection, self.commands["init"])
        return requests.get(new_scan_url, params=self.headers)

    def get_scan_id(self, split_by=16):
        """
        get the ID of the current API scan
        """
        current_scan_id = None
        id_re = re.compile(r"[a-fA-F0-9]{16}")
        api_id_url = "{}{}".format(self.connection, self.commands["id"])
        req = requests.get(api_id_url)
        to_check = str(json.loads(req.content)["tasks"]).lower()
        found = ''.join(id_re.findall(to_check))
        if len(found) > 16:
            data_found = [found[i:i+split_by] for i in range(0, len(found), split_by)]
            for item in data_found:
                if item not in lib.core.settings.ALREADY_USED:
                    lib.core.settings.ALREADY_USED.add(item)
                    current_scan_id = item
        else:
            lib.core.settings.ALREADY_USED.add(found)
            current_scan_id = found
        return current_scan_id

    def start_scan(self, api_id, opts=None):
        """
        start the API scan
        """
        start_scan_url = "{}{}".format(self.connection, self.commands["start"].format(api_id))
        data_dict = {"url": self.to_scan}
        if opts is not None:
            for i in range(0, len(opts)):
                data_dict[opts[i][0]] = opts[i][1]
        post_data = json.dumps(data_dict)
        req = urllib.request.Request(start_scan_url, data=post_data, headers=self.headers)
        return urllib.request.urlopen(req)

    def show_sqlmap_log(self, api_id):
        """
        show the sqlmap log during the API scan
        """
        running_status_url = "{}{}".format(self.connection, self.commands["status"].format(api_id))
        running_log_url = "{}{}".format(self.connection, self.commands["log"].format(api_id))
        status_req = requests.get(running_status_url)
        status_json = json.loads(status_req.content)
        current_status = status_json["status"]
        if current_status != "running":
            raise lib.core.errors.SqlmapFailedStart(
                "sqlmap API failed to start the run, check the client and see what "
                "the problem is and try again..."
            )
        already_displayed = set()
        while current_status == "running":
            current_status = json.loads(requests.get(running_status_url).content)["status"]
            log_req = requests.get(running_log_url)
            log_json = json.loads(log_req.content)
            for i in range(0, len(log_json["log"])):
                if log_json["log"][i]["message"] in already_displayed:
                    pass
                else:
                    print(
                        "sqlmap> [{} {}] {}".format(
                            log_json["log"][i]["time"],
                            log_json["log"][i]["level"],
                            log_json["log"][i]["message"]
                        )
                    )
                already_displayed.add(log_json["log"][i]["message"])


def find_sqlmap(to_find="sqlmap", verbose=False):
    """
    find sqlmap on the users system
    """
    found_path = lib.core.settings.find_application(to_find, verbose=verbose)
    return found_path


def sqlmap_scan_main(url, port=None, verbose=None, opts=None, auto_start=False):
    """
    the main function that will be called and initialize everything
    """

    def ___dict_args():
        """
        create argument tuples for the sqlmap arguments passed by the user
        """
        return {key: value for key, value in opts}

    is_started = lib.core.settings.search_for_process("sqlmapapi.py")

    if auto_start:
        lib.core.settings.logger.error(lib.core.settings.set_color(
            "auto starting sqlmap is not implemented yet, you will need to start "
            "the API manually for now...", level=40
        ))
        lib.core.settings.prompt(
            "press enter when ready to continue..."
        )
        '''lib.core.settings.logger.info(lib.core.settings.set_color(
            "attempting to find sqlmap on your system..."
        ))
        try:
            path = "".join(find_sqlmap("sqlmap", verbose=verbose))
            lib.core.settings.logger.info(lib.core.settings.set_color(
                "attempting to call sqlmap API..."
            ))
            subprocess.Popen(["python {}/{} -s".format(path, "sqlmapapi.py")], shell=True,
                             close_fds=True, stdout=subprocess.PIPE)
            lib.core.settings.logger.info(lib.core.settings.set_color(
                "API started, continuing process..."
                )
            )
            time.sleep(3)
            if not is_started:
                lib.core.settings.prompt(
                    "appears that sqlmap's API was not started successfully, start it manually and press"
                    " enter..."
                )
        except Exception as e:
            print e
            lib.core.settings.logger.error(lib.core.settings.set_color(
                "ran into an error while trying to start the sqlmap API, please do it manually...", level=50
            ))
            lib.core.settings.prompt(
                "press enter when ready to start..."
            )'''
    else:
        if not is_started:
            lib.core.settings.prompt(
                "sqlmap API is not started, start it and press enter to continue..."
            )
    try:
        sqlmap_scan = SqlmapHook(url, port=port)
        lib.core.settings.logger.info(lib.core.settings.set_color(
            "initializing new sqlmap scan with given URL '{}'...".format(url)
        ))
        sqlmap_scan.init_new_scan()
        if verbose:
            lib.core.settings.logger.debug(lib.core.settings.set_color(
                "scan initialized...", level=10
            ))
        lib.core.settings.logger.info(lib.core.settings.set_color(
            "gathering sqlmap API scan ID..."
        ))
        api_id = sqlmap_scan.get_scan_id()
        if verbose:
            lib.core.settings.logger.debug(lib.core.settings.set_color(
                "current sqlmap scan ID: '{}'...".format(api_id), level=10
            ))
        lib.core.settings.logger.info(lib.core.settings.set_color(
            "starting sqlmap scan on url: '{}'...".format(url)
        ))
        if opts:
            if verbose:
                lib.core.settings.logger.debug(lib.core.settings.set_color(
                    "using arguments: '{}'...".format(___dict_args()), level=10
                ))
            lib.core.settings.logger.info(lib.core.settings.set_color(
                "adding arguments to sqlmap API..."
            ))
        else:
            if verbose:
                lib.core.settings.logger.debug(lib.core.settings.set_color(
                    "no arguments passed, skipping...", level=10
                ))
        lib.core.settings.logger.warning(lib.core.settings.set_color(
            "please keep in mind that this is the API, output will "
            "not be saved to log file, it may take a little longer "
            "to finish processing, launching sqlmap...", level=30
        ))
        sqlmap_scan.start_scan(api_id, opts=opts)
        print("-" * 30)
        sqlmap_scan.show_sqlmap_log(api_id)
        print("-" * 30)
    except requests.exceptions.HTTPError as e:
        lib.core.settings.logger.exception(lib.core.settings.set_color(
            "ran into error '{}', seems you didn't start the server, check "
            "the server port and try again...".format(e), level=50
        ))
        pass
    except Exception as e:
        if "HTTPConnectionPool(host='127.0.0.1'" in str(e):
            lib.core.settings.logger.error(lib.core.settings.set_color(
                "sqlmap API is not started, did you forget to start it? "
                "You will need to open a new terminal, cd into sqlmap, and "
                "run `python sqlmapapi.py -s` otherwise pass the correct flags "
                "to auto start the API...", level=40
            ))
            pass
        else:
            lib.core.settings.logger.exception(lib.core.settings.set_color(
                "ran into error '{}', seems something went wrong, error has "
                "been saved to current log file.".format(e), level=50
            ))
            request_issue_creation()
            pass
