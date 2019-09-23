import json
import re

from bs4 import BeautifulSoup
import requests


url = 'https://www.swift.com/standards/data-standards/iban'


def get_raw():
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    link = soup.find('a', attrs={'data-title': 'IBAN Registry (TXT)'})
    # Warning: This document is not in Unicode, but also probably not in any one 8-bit encoding
    # Some names and addresses are Turkish, others French
    # We will ignore this for now, but if ever the names/addresses become relevant, we would
    # need to find a solution
    return requests.get(link['href']).content.decode('windows-1252')


def parse_line(initer):
    in_quote = False
    databuffer = []
    for ch in initer:
        if not in_quote:
            if ch == "\x09":
                yield "".join(databuffer)
                databuffer = []
            elif ch in ("\n", "\r"):
                break
            elif ch == "\"":
                in_quote = True
            else:
                databuffer.append(ch)
        else:
            if ch == "\"":
                in_quote = False
            else:
                databuffer.append(ch)
    if databuffer:
        yield "".join(databuffer)


def parse_txt(raw):
    """
    Turns a string like
    A\t1\t2\t3
    B\t4\t5\t6
    into a list of dictionaries:
    [{"A": "1", "B": "4"}, {"A": "2", "B": "5"}, {"A": "3", "B": "6"}]
    """
    result = []
    raw_iter = iter(raw)
    while True:
        items = list(parse_line(raw_iter))
        if not items:
            break
        key = items.pop(0)
        while len(result) < len(items):
            result.append({})
        for i, item in enumerate(items):
            result[i][key] = item
    return result


def parse_positions(bban_length, spec):
    pattern = r'(.*?)(\d+)\s*(?:-|to)\s*(\d+)'
    matches = re.findall(pattern, spec)
    positions = {'bank_code': [0, 0], 'branch_code': [0, 0], 'account_code': [0, 0]}

    def match_to_range(match):
        return [int(match[1]) - 1, int(match[2])]

    positions['account_code'] = [0, bban_length]
    if matches:
        positions['bank_code'] = match_to_range(matches[0])
        positions['account_code'][0] = positions['bank_code'][1]
    if len(matches) > 1 and 'Branch' in matches[1][0]:
        positions['branch_code'] = match_to_range(matches[1])
        positions['account_code'][0] = positions['branch_code'][1]
    else:
        positions['branch_code'] = [positions['bank_code'][1], positions['bank_code'][1]]
    return positions


if __name__ == '__main__':
    #raw = get_raw()
    raw = open('foo-0', encoding='windows-1254').read()
    data = parse_txt(raw)
    registry = {}
    for row in data:
        codes = re.findall(r'[A-Z]{2}', row["IBAN prefix country code (ISO 3166)"] + " " + row["Country code includes other countries/territories"])
        entry = {
            'bban_spec': row['BBAN structure'],
            'bban_length': row['BBAN length'],
            'iban_spec': re.match(r'[A-Za-z0-9!]+', row['IBAN structure']).group(0),
            'iban_length': row['IBAN length'],
        }
        if entry['bban_spec'] == 'Not in use':
            entry['bban_spec'] = re.sub(r'[A-Z]{2}2!n', '', entry['iban_spec'])
        entry['bban_spec'] = entry['bban_spec'].replace(' ', '')

        if entry['bban_length'].endswith("!n"):
            # Costa Rica (in 2019.09)
            entry["bban_length"] = entry["bban_length"][:-2]

        if entry['iban_length'].endswith("!n"):
            # El Salvador (in 2019.09)
            entry["iban_length"] = entry["iban_length"][:-2]
        entry["iban_length"] = int(entry["iban_length"])

        if entry['bban_length'] == 'Not in use':
            entry['bban_length'] = entry['iban_length'] - 4
        else:
            entry['bban_length'] = int(entry['bban_length'])

        entry['positions'] = parse_positions(
            entry['bban_length'],
            row['Bank identifier position within the BBAN'])

        for code in codes:
            registry[code] = entry

    with open('schwifty/iban-registry.json', 'w+') as fp:
        json.dump(registry, fp, indent=2)
