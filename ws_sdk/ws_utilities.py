import copy
import json
import logging
import requests
import os
import shutil
from dataclasses import dataclass
from typing import Callable
from ws_sdk.ws_constants import *


def is_token(token: str) -> bool:
    return False if token is None or len(token) != 64 else True


def convert_dict_list_to_dict(lst: list,
                              key_desc: str or tuple) -> dict:
    """
    Function to convert list of dictionaries into dictionary of dictionaries according to specified key
    :param lst: List of dictionaries
    :param key_desc: the key or keys (as tuple) description of the returned dictionary (a key can be str or dict)
    :return: dict with key according to key description and the dictionary value
    """
    def create_key(key_desc: str or tuple,
                   dct: dict) -> str or tuple:
        ret = None
        if isinstance(key_desc, str):
            return dct[key_desc]
        elif isinstance(key_desc, tuple):
            ret = []
            for x in key_desc:
                try:
                    if isinstance(x, str) and dct[x]:
                        ret.append(dct[x])
                        logging.debug(f"Key type is a string: {dct[x]}")
                    elif isinstance(x, dict):
                        for key, value in x.items():
                            logging.debug(f"Key type is a dict: {key}")
                            internal_dict = dct.get(key, None)
                            if internal_dict:
                                ret.append(internal_dict.get(value, None))
                except KeyError:
                    logging.error(f"Key: {key_desc} was not found")
                    return None
            logging.debug(f"Key is tuple: {ret}")
            return tuple(ret)
        else:
            logging.error(f"Unsupported key_desc: {type(key_desc)}")
            return None

    ret = {}
    for i in lst:
        curr_key = create_key(key_desc, i)
        ret[curr_key] = i

    return ret


def get_all_req_schemas(ws_conn) -> dict:
    supported_requests = ws_conn.__generic_get__(get_type="SupportedRequests", token_type="")['supportedRequests']
    req_schema_list = {}
    for req in supported_requests:
        logging.info(f"Calling on {req}")
        req_schema = ws_conn.__generic_get__(get_type="RequestSchema", token_type="", kv_dict={"request": req})
        req_schema_list[req] = req_schema

    return req_schema_list


def get_report_types():
    from ws_sdk import web
    report_types = set()
    class_dict = dict(web.WS.__dict__)
    for f in class_dict.items():
        if web.report_metadata.__name__ in str(f[1]):
            report_types.add(f[0].replace('get_',''))

    return report_types


def get_lib_metadata_by_name(language: str) -> LibMetaData.LibMetadata:
    """
    Method that Returns matadata on a language
    :type language: language to return metadata on
    :rtype: NamedTuple
    """
    lc_lang = language.lower()
    for lang_metadata in LibMetaData.L_TYPES:
        if lang_metadata.language == lc_lang:
            return lang_metadata
    logging.error("Language is unsupported")

    return None


def get_package_managers_by_language(language: str) -> list:
    lang_md = get_lib_metadata_by_name(language=language)

    return lang_md.package_manager if lang_md else None

def break_filename(filename: str) -> tuple:
    import re
    return {"suffix": re.search(r'.([a-zA-z0-9]+$)', filename).group(1),
            'name': re.search(r'(^[a-zA-Z0-9-]+)(?=-)', filename).group(1),
            'version': re.search(r'-((?!.*-).+)(?=\.)', filename).group(1)}

def get_full_ws_url(url) -> str:
    if url is None:
        url = 'saas'
    if url in ['saas', 'saas-eu', 'app', 'app-eu']:
        url = f"https://{url}.whitesourcesoftware.com"

    return url

def call_gh_api(url: str):
    logging.debug(f"Calling url: {url}")
    try:
        res = requests.get(url=url, headers=GH_HEADERS)
    except requests.RequestException:
        logging.exception("Error getting last release")

    return res

def parse_ua_conf(filename: str) -> dict:
    """
    Function that parse ua conf (i.e. wss-unified-agent.config) and returns it as a dictionary
    :param filename:
    :return:
    """
    with open(filename, 'r') as ua_conf_f:
        ua_conf_dict = {}
        for line in ua_conf_f:
            splitted_l = line.strip().split("=")
            if len(splitted_l) > 1:
                ua_conf_dict[splitted_l[0]] = splitted_l[1]

    return ua_conf_dict

class WsConfiguration:
    ...

def convert_ua_conf_f_to_vars(filename: str) -> WsConfiguration:
    """
    Load UA conf file and create a class with all key as variables
    :param filename: file name to load
    :return: Class with all attributes as variables.
    """
    conf = parse_ua_conf(filename)
    ws_configuration = WsConfiguration()
    for k, v in conf.items():
        if k[0] == '#':
            k = k[1:]
            v = ""
        setattr(ws_configuration, k.replace('.', '_'), v)

    return ws_configuration

def generate_conf_ev(ws_configuration: WsConfiguration) -> dict:
    def to_str(t):
        return  ",".join(t) if isinstance(t, (set, list)) else str(t)

    """
    Convert WsConfiguration into UA env vars dictionary
    :param ws_configuration:
    :return: dictionary of env vars
    """
    return {**os.environ,
            **{f"WS_" + k.upper(): to_str(v) for k, v in ws_configuration.__dict__.items() if v is not None}}


def init_ua(path: str):
    download_ua(path)


def download_ua(path: str,
                inc_ua_jar_file: bool = True,
                inc_ua_conf_file: bool = True):
    def download_ua_file(f_details: tuple):
        file_p = os.path.join(path, f_details[0])
        if os.path.exists(file_p):
            logging.debug(f"Backing up previous {f_details[0]}")
            shutil.move(file_p, f"{file_p}.bkp")
        logging.debug(f"Downloading WS Unified Agent (version: {get_latest_ua_release_version()}) to {file_p}")
        resp = requests.get(url=f_details[1])
        with open(file_p, 'wb') as f:
            f.write(resp.content)

    if inc_ua_jar_file:
        download_ua_file(UA_JAR_T)

    if inc_ua_conf_file:
        download_ua_file(UA_CONF_T)


def get_latest_ua_release_version() -> str:
    ver = get_latest_ua_release_url()['tag_name']
    logging.debug(f"Latest Unified Agent version: {ver}")

    return ver


def get_latest_ua_release_url() -> dict:
    res = call_gh_api(url=LATEST_UA_URL)

    return json.loads(res.text)

