#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gzip
import re
import requests
import sys

git_branch="master"
git_url="https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git"

DASHBOARD_API = "https://dashboard.kernelci.org/api/"

hardware = [
    "raspberrypi,4-model-b",
    "google,kevin-rev15",
    "google,veyron-jaq-rev4",
    "fsl,imx6q",
 ]

def fetch_test_details(id, hardware):
    target = f'tests/test/{id}'
    url = f'{DASHBOARD_API}{target}'
    r = requests.get(url)
    log_url = r.json()['log_url']

    # XXX this is a PoC, so just when logs goes None
    if not log_url:
        return

    m = re.search('https://kciapistagingstorage1.file.core.windows.net/production/(baseline.*)/log.txt.*$', log_url)
    fname = m.group(1)

    log_gz = requests.get(log_url)
    log = gzip.decompress(log_gz.content)
    with open(f'{fname}-{hardware}.txt', mode="wb") as file:
        file.write(log)

def fetch_boot_logs(hash):
    target= f'tree/{hash}/full'
    url = f'{DASHBOARD_API}{target}?origin=maestro&git_branch={git_branch}&git_url={git_url}'
    r = requests.get(url)
    for boot in r.json()['bootHistory']:
        if boot['hardware']:
            for h in hardware:
                if h in boot['hardware']:
                    fetch_test_details(boot['id'], h)
                    break

if __name__ == "__main__":
    fetch_boot_logs(sys.argv[1])